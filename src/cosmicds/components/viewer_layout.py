import solara
from glue.viewers.common.viewer import Viewer
from reacton import ipyvuetify as rv
from cosmicds.utils import make_figure_autoresize

@solara.component
def ViewerLayout(viewer: Viewer, height=400):
    with rv.Card() as main:
        with rv.Toolbar(dense=True, class_="toolbar"):
            with rv.ToolbarTitle():
                title_container = rv.Html(tag="div", class_ = "toolbar-title")

            rv.Spacer()
            toolbar_container = rv.Html(tag="div")

        viewer_container = rv.Html(tag="div", style_=f"width: 100%; height: {height}px")

        def _setup():
            title_widget = solara.get_widget(title_container)
            title_widget.children = (viewer.state.title or "VIEWER",)

            toolbar_widget = solara.get_widget(toolbar_container)
            toolbar_widget.children = (viewer.toolbar,)

            viewer_widget = solara.get_widget(viewer_container)
            viewer_widget.children = (viewer.figure_widget,)

            make_figure_autoresize(viewer.figure_widget, 400)

            def cleanup():
                for cnt in (title_widget, toolbar_widget, viewer_widget):
                    cnt.children = ()

            return cleanup

        solara.use_effect(_setup, dependencies=[])

    return main        