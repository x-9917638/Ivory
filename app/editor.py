from textual import events
from textual.events import Click
from textual.screen import Screen
from textual.widgets import TextArea, Header, Footer
from textual.message import Message
from textual.widget import Widget
from textual.app import ComposeResult, RenderResult
from textual.reactive import reactive

from textual.widgets.text_area import TextAreaTheme

from rich.style import Style

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from rich.text import Text
# Main editing area should be mostly transparent so that the reader screene with the nice rendered markup shows,
# lkke how obsidian does that preview while editing thing
# obviously should be able to turn off

brackets = {
    ")": 0,
    "]": 0,
    "}": 0,
} # Track auto-closed brackets


class ToggleModeIcon(Widget):
    """Display an 'icon' on the right of the header."""
    
    DEFAULT_CSS = """
    ToggleModeIcon {
        dock: right;
        width: 10;
        padding: 0 1;
        content-align: center middle;
    }

    ToggleModeIcon:hover {
        background: $foreground 10%;
    }
    """

    icon = reactive("")

    class Clicked(Message):
        def __init__(self, editing: bool) -> None:
            self.editing = editing
            super().__init__()


    def __init__(self) -> None:
        super().__init__()
        self.editing = True
        self.icon_map = {
            False: "",
            True: ""
        }

    async def on_click(self, event: Click) -> None:
        """Return message, change icon if clicked"""
        event.stop()
        
        self.editing = not self.editing
        
        self.post_message(self.Clicked(self.editing))
        self.icon = self.icon_map[self.editing]

    def render(self) -> RenderResult:
        """Render the header icon.

        Returns:
            The rendered icon.
        """
        return self.icon


class AppHeader(Header):
    def compose(self) -> ComposeResult:
        header_widgets = [widget for widget in super().compose()]
        yield header_widgets[0] # Cmd icon
        yield header_widgets[1] # Title
        yield ToggleModeIcon()
    
    def _on_click(self, event: events.Click):
        event.prevent_default()
       
class Editor(TextArea):
    def on_mount(self) -> None:
        self.auto_indented = False
        self.auto_bulleted = False


    def _line_plain(self, row: int) -> str:
        return self.get_line(row).plain
        

    def _leading_whitespace(self, s: str) -> int:
        i = 0
        while i < len(s) and s[i] in (" ", "\t"):
            i += 1
        return i

    def _get_bullet_prefix(self, after_ws_text: str) -> str:
        for prefix in ("- ", "* ", "+ "):
            if after_ws_text.startswith(prefix):
                return prefix
        return ""

    def _on_key(self, event: events.Key) -> None:
        match event.key:
            case "left_square_bracket":
                self.insert("[]")
                brackets["]"] += 1
                self.move_cursor_relative(columns=-1)
                event.prevent_default()

            case "left_curly_bracket":
                self.insert("{}")
                brackets["}"] += 1
                self.move_cursor_relative(columns=-1)
                event.prevent_default()

            case "left_parenthesis":
                self.insert("()")
                brackets[")"] += 1
                self.move_cursor_relative(columns=-1)
                event.prevent_default()

            case "ctrl+backspace":
                self.action_delete_word_left()
            case "ctrl+delete":
                self.action_delete_word_right()

            case "enter":
                row, col = self.cursor_location
                line_text = self._line_plain(row)
                indent_len = self._leading_whitespace(line_text)
                bullet = self._get_bullet_prefix(line_text[indent_len:])
                at_line_end = col == len(line_text)

                if at_line_end and bullet and line_text[indent_len + len(bullet):].strip() == "":
                    width = self.indent_width
                    if indent_len > 0:
                        new_indent = max(0, indent_len - width)
                        self.delete((row, 0), (row, len(line_text)))
                        self.insert(" " * new_indent + bullet)
                        self.auto_indented = new_indent > 0
                        self.auto_bulleted = True
                        event.prevent_default()
                        event.stop()
                        return
                    else:
                        self.delete((row, indent_len), (row, indent_len + len(bullet)))
                        self.auto_bulleted = False
                        self.auto_indented = False
                        event.prevent_default()
                        event.stop()
                        return

                if at_line_end and not bullet and line_text[indent_len:].strip() == "" and indent_len > 0:
                    width = self.indent_width
                    new_indent = max(0, indent_len - width)
                    self.delete((row, 0), (row, indent_len))
                    if new_indent:
                        self.insert(" " * new_indent)
                        self.auto_indented = True
                    else:
                        self.auto_indented = False
                    self.auto_bulleted = False
                    event.prevent_default()
                    event.stop()
                    return

                self.insert(self.document.newline)
                if indent_len > 0:
                    self.insert(" " * indent_len)
                    self.auto_indented = True
                else:
                    self.auto_indented = False
                if bullet:
                    self.insert(bullet)
                    self.auto_bulleted = True
                else:
                    self.auto_bulleted = False
                event.prevent_default()
                event.stop()
                return

            case "backspace":
                row, col = self.cursor_location
                line_text = self._line_plain(row)
                indent_len = self._leading_whitespace(line_text)
                bullet = self._get_bullet_prefix(line_text[indent_len:])

                if bullet and col <= indent_len + len(bullet) and col >= indent_len:
                    self.delete((row, indent_len), (row, indent_len + len(bullet)))
                    self.auto_bulleted = False
                    event.prevent_default()
                    return

                if indent_len > 0 and col <= indent_len:
                    width = self.indent_width
                    remove = min(width, col, indent_len)
                    self.delete((row, col - remove), (row, col))
                    self.auto_indented = False
                    event.prevent_default()
                    return
            
            case "tab":
                # Let <tab> just move the bullet up 1 cause otherwise it feels annoying
                if self.auto_bulleted:
                    event.prevent_default()
                    self.insert(" " * self.indent_width, (self.cursor_location[0], 0))
                    self.auto_bulleted = False

        # Close bracket wont dobule up if editor auto closed a bracket b4
        ch = event.character
        if ch in brackets and brackets.get(ch, 0) > 0:
            index = self.document.get_index_from_location(self.cursor_location)
            text = self.document.text
            if 0 <= index < len(text) and text[index:index + 1] == ch:
                brackets[ch] -= 1
                self.move_cursor_relative(columns=1)
                event.prevent_default()
        


class EditorScreen(Screen):

    CSS_PATH = "../styles/editor.tcss"

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield Footer()
        editor = Editor.code_editor(
            tab_behavior="indent",
            language="markdown",
            classes="Editor"
        )
        editor.register_theme(MONOKAI_CUSTOM)
        editor.theme="monokai-custom"
        editor.indent_type="spaces"
        editor.indent_width=2
        editor.show_line_numbers=True
        yield editor


MONOKAI_CUSTOM = TextAreaTheme(
    # Textual's builtin theme but I modified a  little to have transparent lines
    name="monokai-custom",
    gutter_style=Style(color="#90908a", bgcolor="#272822"),
    cursor_style=Style(color="#272822", bgcolor="#f8f8f0"),
    # cursor_line_style=Style(bgcolor="#3e3d32"),
    cursor_line_gutter_style=Style(color="#c2c2bf", bgcolor="#3e3d32"),
    bracket_matching_style=Style(bgcolor="#838889", bold=True),
    selection_style=Style(bgcolor="#65686a"),
    syntax_styles={
        "string": Style(color="#E6DB74"),
        "string.documentation": Style(color="#E6DB74"),
        "comment": Style(color="#75715E"),
        "heading.marker": Style(color="#90908a"),
        "keyword": Style(color="#F92672"),
        "operator": Style(color="#f8f8f2"),
        "repeat": Style(color="#F92672"),
        "exception": Style(color="#F92672"),
        "include": Style(color="#F92672"),
        "keyword.function": Style(color="#F92672"),
        "keyword.return": Style(color="#F92672"),
        "keyword.operator": Style(color="#F92672"),
        "conditional": Style(color="#F92672"),
        "number": Style(color="#AE81FF"),
        "float": Style(color="#AE81FF"),
        "class": Style(color="#A6E22E"),
        "type": Style(color="#A6E22E"),
        "type.class": Style(color="#A6E22E"),
        "type.builtin": Style(color="#F92672"),
        "variable.builtin": Style(color="#f8f8f2"),
        "function": Style(color="#A6E22E"),
        "function.call": Style(color="#A6E22E"),
        "method": Style(color="#A6E22E"),
        "method.call": Style(color="#A6E22E"),
        "boolean": Style(color="#66D9EF", italic=True),
        "constant.builtin": Style(color="#66D9EF", italic=True),
        "json.null": Style(color="#66D9EF", italic=True),
        "regex.punctuation.bracket": Style(color="#F92672"),
        "regex.operator": Style(color="#F92672"),
        "html.end_tag_error": Style(color="red", underline=True),
        "tag": Style(color="#F92672"),
        "yaml.field": Style(color="#F92672", bold=True),
        "json.label": Style(color="#F92672", bold=True),
        "toml.type": Style(color="#F92672"),
        "toml.datetime": Style(color="#AE81FF"),
        "css.property": Style(color="#AE81FF"),
        "heading": Style(color="#F92672", bold=True),
        "bold": Style(bold=True),
        "italic": Style(italic=True),
        "strikethrough": Style(strike=True),
        "link.label": Style(color="#F92672"),
        "link.uri": Style(color="#66D9EF", underline=True),
        "list.marker": Style(color="#90908a"),
        "inline_code": Style(color="#E6DB74"),
        "punctuation.bracket": Style(color="#f8f8f2"),
        "punctuation.delimiter": Style(color="#f8f8f2"),
        "punctuation.special": Style(color="#f8f8f2"),
    },
)