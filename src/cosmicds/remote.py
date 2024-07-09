from solara_enterprise import auth
import hashlib
import os
from requests import Session
from functools import cached_property

from .state import BaseLocalState, BaseState, GlobalState
from solara import Reactive
from solara.lab import Ref
from cosmicds.logger import setup_logger

logger = setup_logger("API")


class BaseAPI:
    API_URL = "https://api.cosmicds.cfa.harvard.edu"

    @cached_property
    def request_session(self):
        """
        Returns a `requests.Session` object that has the relevant authorization
        parameters to interface with the CosmicDS API server (provided that
        environment variables are set correctly).
        """
        session = Session()
        session.headers.update({"Authorization": os.getenv("CDS_API_KEY")})
        return session

    @property
    def hashed_user(self):
        if auth.user.value is None:
            logger.error("Failed to create hash: user not authenticated.")
            return "User not authenticated"

        userinfo = auth.user.value.get("userinfo")

        if not ("email" in userinfo or "name" in userinfo):
            logger.error("Failed to create hash: not authentication information.")
            return

        user_ref = userinfo.get("email", userinfo["name"])

        hashed = hashlib.sha1(
            (user_ref + os.environ["SOLARA_SESSION_SECRET_KEY"]).encode()
        ).hexdigest()

        return hashed

    @property
    def user_exists(self):
        r = self.request_session.get(f"{self.API_URL}/student/{self.hashed_user}")
        return r.json()["student"] is not None

    def load_user_info(self, story_name: str, state: Reactive[GlobalState]):
        student_json = self.request_session.get(
            f"{self.API_URL}/student/{self.hashed_user}"
        ).json()["student"]

        class_json = self.request_session.get(
            f"{self.API_URL}/class-for-student-story/{state.value.student.id}/{story_name}"
        ).json()

        student_id = Ref(state.fields.student.id)
        student_id.set(student_json["id"])
        Ref(state.fields.classroom.class_info).set(class_json["class"])
        Ref(state.fields.classroom.size).set(class_json["size"])

        logger.info("Loaded user info for user `%s`.", state.value.student.id)

    def create_new_user(
        self, story_name: str, class_code: str, state: Reactive[GlobalState]
    ):
        r = self.request_session.get(f"{self.API_URL}/student/{self.hashed_user}")
        student = r.json()["student"]

        if student is not None:
            logger.error(
                "Failed to create user `%s`: user already exists.", self.hashed_user
            )
            return

        r = self.request_session.post(
            f"{self.API_URL}/student-sign-up",
            json={
                "username": self.hashed_user,
                "password": "",
                "institution": "",
                "email": f"{self.hashed_user}",
                "age": 0,
                "gender": "undefined",
                "classroomCode": class_code,
            },
        )

        if r.status_code != 200:
            logger.error("Failed to create new user.")
            return

        logger.info(
            "Created new user `%s` with class code '%s'.",
            self.hashed_user,
            class_code,
        )

        self.load_user_info(story_name, state)

    def put_stage_state(
        self,
        global_state: Reactive[GlobalState],
        local_state: Reactive[BaseLocalState],
        component_state: Reactive[BaseState],
    ):
        raise NotImplementedError()

    def get_stage_state(
        self,
        global_state: Reactive[GlobalState],
        local_state: Reactive[BaseLocalState],
        component_state: Reactive[BaseState],
    ) -> BaseState | None:
        stage_json = (
            self.request_session.get(
                f"{self.API_URL}/stage-state/{global_state.value.student.id}/"
                f"{local_state.value.story_id}/{component_state.value.stage_id}"
            )
            .json()
            .get("state", None)
        )

        if stage_json is None:
            logger.error(
                "Failed to retrieve stage state for story `%s` for user `%s`.",
                local_state.value.story_id,
                global_state.value.student.id,
            )
            return

        component_state.set(component_state.value.__class__(**stage_json))

        logger.info("Updated component state from database.")

        return component_state.value

    def delete_stage_state(
        self,
        global_state: Reactive[GlobalState],
        local_state: Reactive[BaseLocalState],
        component_state: Reactive[BaseState],
    ):
        r = self.request_session.delete(
            f"{self.API_URL}/stage-state/{global_state.value.student.id}/"
            f"{local_state.value.story_id}/{component_state.value.stage_id}"
        )

        if r.status_code != 200:
            logger.error(
                "Stage state for stage `%s`, story `%s` user `%s` did not exist in database.",
                component_state.value.stage_id,
                local_state.value.story_id,
                global_state.value.student.id,
            )
            return

        result = r.json()
        if not result.get("success", False):
            logger.error(
                "Error deleting stage state for stage `%s`, story `%s` user `%s`.",
                component_state.value.stage_id,
                local_state.value.story_id,
                global_state.value.student.id,
            )
            return

    def get_story_state(
        self, global_state: Reactive[GlobalState], local_state: Reactive[BaseLocalState]
    ) -> BaseLocalState | None:
        story_json = (
            self.request_session.get(
                f"{self.API_URL}/story-state/{global_state.value.student.id}/"
                f"{local_state.value.story_id}"
            )
            .json()
            .get("state", None)
        )

        if story_json is None:
            logger.error(
                "Failed to retrieve state for story `%s` for user `%s`.",
                local_state.value.story_id,
                global_state.value.student.id,
            )
            return

        # global_state_json = story_json.get("app", {})
        # global_state_json.pop("student")
        # global_state.set(global_state.value.__class__(**global_state_json))

        local_state_json = story_json.get("story", {})
        local_state.set(local_state.value.__class__(**local_state_json))

        logger.info("Updated local state from database.")

        return local_state.value

    def put_story_state(
        self,
        global_state: Reactive[GlobalState],
        local_state: Reactive[BaseLocalState],
    ):
       raise NotImplementedError() 

    @staticmethod
    def clear_user(state: Reactive[GlobalState]):
        Ref(state.fields.student.id).set(0)
        Ref(state.fields.classroom.class_info).set({})
        Ref(state.fields.classroom.size).set(0)


BASE_API = BaseAPI()
