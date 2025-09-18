from textual.app import App
from textual.widgets import Header, Footer
from app.editor import EditorScreen, ToggleModeIcon

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from textual.app import ComposeResult

class Ivory(App):
    """Main application class for Ivory"""
    

    CSS_PATH = "styles/main.tcss"

    # SCREENS = {"editor": EditorScreen}

    def on_mount(self) -> None:
        self.push_screen(EditorScreen())

    def compose(self) -> "ComposeResult":
        yield Header()
        yield Footer()
        # editor = Editor.code_editor(
        #     tab_behavior="indent",
        #     language="markdown",
        #     classes="Editor",
        #     theme="css"
        # )
        # editor.indent_type="spaces"
        # editor.indent_width=2
        # editor.show_line_numbers=True
        # yield editor
    
    def on_toggle_mode_icon_clicked(self, message: ToggleModeIcon.Clicked):
        # push reader screen to top
        print(message)
        message.stop()

if __name__ == "__main__":
    app = Ivory()
    app.run()