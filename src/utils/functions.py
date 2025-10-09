import discord, asyncio, os
import tomlkit as tk
from pathlib import Path
from typing import List, Union, Tuple, Dict, Any, Callable

# ==================== MODAL CLASSES ====================


class Modal(discord.ui.Modal):
    """Main modal class with optional page support."""

    def __init__(
        self,
        title: str,
        pages: List[List],
        descs: List[str] = None,
        page_required: List[bool] = None,
        confirm_msg: Union[str, Callable] = None,
        skip_msg: str = None,
        done_msg: str = None,
    ):
        self.values = {}
        self.page = 0
        self.pages = pages
        self.descs = descs or [f"Page {i+1}" for i in range(len(pages))]
        self.page_required = page_required or [True] + [False] * (len(pages) - 1)
        self.done_future = asyncio.Future()

        self.confirm_msg = (
            confirm_msg or "**Optional Settings**\nWould you like to configure {desc}?"
        )
        self.skip_msg = (
            skip_msg or "✅ Configuration saved! (Optional settings skipped)"
        )
        self.done_msg = done_msg or "✅ All configurations saved!"

        # Validate page sizes
        for i, page_fields in enumerate(pages):
            if len(page_fields) > 5:
                raise ValueError(f"Page {i+1} has too many fields (max 5).")

        super().__init__(title=self._get_title(title, 0))
        self._add_fields(self.pages[0])

    def _get_title(self, base: str, num: int) -> str:
        if len(self.pages) > 1:
            return f"{base} ({num + 1}/{len(self.pages)})"
        return base

    def _add_fields(self, fields: List):
        for field in fields:
            if isinstance(field, dict):
                name = field["name"]
                req = field.get("required", True)
                place = field.get("placeholder", f"Enter {name}...")
                style = field.get("style", discord.InputTextStyle.short)
                default = field.get("default", "")
            elif isinstance(field, tuple):
                name, req = field
                place = f"Enter {name}..."
                style = discord.InputTextStyle.short
                default = ""
            else:
                name = field
                req = True
                place = f"Enter {name}..."
                style = discord.InputTextStyle.short
                default = ""

            item = discord.ui.InputText(
                label=name,
                placeholder=place,
                required=req and self.page_required[self.page],
                style=style,
                value=default,
            )
            self.add_item(item)
            self.values[name] = None

    async def callback(self, inter: discord.Interaction):
        # Save current page values
        for i, field in enumerate(self.pages[self.page]):
            name = self._get_name(field)
            self.values[name] = self.children[i].value

        # Validate required fields if page is required
        if self.page_required[self.page]:
            missing_fields = []
            for i, field in enumerate(self.pages[self.page]):
                field_name = self._get_name(field)
                field_required = self._is_field_required(field)

                if field_required and not self.values[field_name]:
                    missing_fields.append(field_name)

            if missing_fields:
                await inter.response.send_message(
                    f"❌ Please fill out all required fields: {', '.join(missing_fields)}",
                    ephemeral=True,
                )
                return

        # Check for more pages
        if self.page < len(self.pages) - 1:
            await self._ask_next(inter)
        else:
            await inter.response.send_message(self.done_msg, ephemeral=True)
            if not self.done_future.done():
                self.done_future.set_result(self.values)
            self.stop()

    def _get_name(self, field) -> str:
        if isinstance(field, dict):
            return field["name"]
        elif isinstance(field, tuple):
            return field[0]
        else:
            return field

    def _is_field_required(self, field) -> bool:
        if isinstance(field, dict):
            return field.get("required", True)
        elif isinstance(field, tuple):
            return field[1]
        else:
            return True

    def _get_confirm_message(self, desc: str, next_page_required: bool) -> str:
        if next_page_required:
            return f"**Required Settings**\nPlease configure {desc} to continue."

        if callable(self.confirm_msg):
            return self.confirm_msg(desc)
        else:
            return self.confirm_msg.format(desc=desc)

    async def _ask_next(self, inter: discord.Interaction):
        next_page = self.page + 1
        desc = self.descs[next_page]
        next_page_required = self.page_required[next_page]
        message = self._get_confirm_message(desc, next_page_required)

        if next_page_required:
            await self._show_next_page(inter)
        else:
            view = View(
                base=self.title.split(" (")[0],
                pages=self.pages,
                descs=self.descs,
                page_required=self.page_required,
                page=next_page,
                values=self.values,
                confirm_msg=self.confirm_msg,
                skip_msg=self.skip_msg,
                done_msg=self.done_msg,
                done_future=self.done_future,
            )
            await inter.response.send_message(message, view=view, ephemeral=True)

    async def _show_next_page(self, inter: discord.Interaction):
        self.page += 1
        modal = NextModal(
            base=self.title.split(" (")[0],
            pages=self.pages,
            descs=self.descs,
            page_required=self.page_required,
            page=self.page,
            values=self.values,
            confirm_msg=self.confirm_msg,
            skip_msg=self.skip_msg,
            done_msg=self.done_msg,
            done_future=self.done_future,
        )
        await inter.response.send_modal(modal)
        await modal.wait()
        self.values.update(modal.values)
        if not self.done_future.done():
            self.done_future.set_result(self.values)
        self.stop()

    async def wait_until_done(self):
        """Wait until the entire multi-page process is complete."""
        return await self.done_future


class View(discord.ui.View):
    """View for continue/skip buttons."""

    def __init__(
        self,
        base: str,
        pages: List,
        descs: List[str],
        page_required: List[bool],
        page: int,
        values: Dict,
        confirm_msg: Union[str, Callable] = None,
        skip_msg: str = None,
        done_msg: str = None,
        done_future: asyncio.Future = None,
    ):
        super().__init__(timeout=120)
        self.base = base
        self.pages = pages
        self.descs = descs
        self.page_required = page_required
        self.page = page
        self.values = values
        self.confirm_msg = confirm_msg
        self.skip_msg = skip_msg
        self.done_msg = done_msg
        self.done_future = done_future

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.primary)
    async def yes_btn(self, button: discord.ui.Button, inter: discord.Interaction):
        # Send the modal FIRST, as the initial response
        modal = NextModal(
            base=self.base,
            pages=self.pages,
            descs=self.descs,
            page_required=self.page_required,
            page=self.page,
            values=self.values,
            confirm_msg=self.confirm_msg,
            skip_msg=self.skip_msg,
            done_msg=self.done_msg,
            done_future=self.done_future,
        )
        await inter.response.send_modal(modal)

        # Then, edit the original message to disable the buttons
        # You need a way to get the original message to do this
        for item in self.children:
            item.disabled = True
        await inter.edit_original_response(
            view=self
        )  # Use this to edit the message that contained the button

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary)
    async def no_btn(self, btn: discord.ui.Button, inter: discord.Interaction):
        if not self.page_required[self.page]:
            for item in self.children:
                item.disabled = True
            await inter.response.edit_message(content=self.skip_msg, view=self)
            if self.done_future and not self.done_future.done():
                self.done_future.set_result(self.values)
            self.stop()
        else:
            await inter.response.send_message(
                "❌ This page contains required settings and cannot be skipped.",
                ephemeral=True,
            )

    async def on_timeout(self):
        if self.done_future and not self.done_future.done():
            self.done_future.set_result(self.values)


class NextModal(discord.ui.Modal):
    """Modal for subsequent pages."""

    def __init__(
        self,
        base: str,
        pages: List,
        descs: List[str],
        page_required: List[bool],
        page: int,
        values: Dict,
        confirm_msg: Union[str, Callable] = None,
        skip_msg: str = None,
        done_msg: str = None,
        done_future: asyncio.Future = None,
    ):
        super().__init__(title=f"{base} ({page + 1}/{len(pages)})")

        self.base = base
        self.pages = pages
        self.descs = descs
        self.page_required = page_required
        self.page = page
        self.values = values.copy()
        self.confirm_msg = confirm_msg
        self.skip_msg = skip_msg
        self.done_msg = done_msg
        self.done_future = done_future

        for field in pages[page]:
            if isinstance(field, dict):
                name = field["name"]
                field_req = field.get("required", True)
                place = field.get("placeholder", f"Enter {name}...")
                style = field.get("style", discord.InputTextStyle.short)
                default = field.get("default", "")
            elif isinstance(field, tuple):
                name, field_req = field
                place = f"Enter {name}..."
                style = discord.InputTextStyle.short
                default = ""
            else:
                name = field
                field_req = True
                place = f"Enter {name}..."
                style = discord.InputTextStyle.short
                default = ""

            item = discord.ui.InputText(
                label=name,
                placeholder=place,
                required=field_req and page_required[page],
                style=style,
                value=default,
            )
            self.add_item(item)
            self.values[name] = None

    async def callback(self, inter: discord.Interaction):
        for i, field in enumerate(self.pages[self.page]):
            name = self._get_name(field)
            self.values[name] = self.children[i].value

        if self.page_required[self.page]:
            missing_fields = []
            for i, field in enumerate(self.pages[self.page]):
                field_name = self._get_name(field)
                field_required = self._is_field_required(field)
                if field_required and not self.values[field_name]:
                    missing_fields.append(field_name)
            if missing_fields:
                await inter.response.send_message(
                    f"❌ Please fill out all required fields: {', '.join(missing_fields)}",
                    ephemeral=True,
                )
                return

        if self.page < len(self.pages) - 1:
            await self._ask_next(inter)
        else:
            await inter.response.send_message(self.done_msg, ephemeral=True)
            if self.done_future and not self.done_future.done():
                self.done_future.set_result(self.values)
            self.stop()

    def _get_name(self, field) -> str:
        if isinstance(field, dict):
            return field["name"]
        elif isinstance(field, tuple):
            return field[0]
        else:
            return field

    def _is_field_required(self, field) -> bool:
        if isinstance(field, dict):
            return field.get("required", True)
        elif isinstance(field, tuple):
            return field[1]
        else:
            return True

    def _get_confirm_message(self, desc: str, next_page_required: bool) -> str:
        if next_page_required:
            return f"**Required Settings**\nPlease configure {desc} to continue."
        if callable(self.confirm_msg):
            return self.confirm_msg(desc)
        else:
            return self.confirm_msg.format(desc=desc)

    async def _ask_next(self, inter: discord.Interaction):
        next_page = self.page + 1
        desc = self.descs[next_page]
        next_page_required = self.page_required[next_page]
        message = self._get_confirm_message(desc, next_page_required)

        if next_page_required:
            await self._show_next_page(inter)
        else:
            view = View(
                base=self.base,
                pages=self.pages,
                descs=self.descs,
                page_required=self.page_required,
                page=next_page,
                values=self.values,
                confirm_msg=self.confirm_msg,
                skip_msg=self.skip_msg,
                done_msg=self.done_msg,
                done_future=self.done_future,
            )
            await inter.response.send_message(message, view=view, ephemeral=True)
            self.stop()

    async def _show_next_page(self, inter: discord.Interaction):
        next_page = self.page + 1
        modal = NextModal(
            base=self.base,
            pages=self.pages,
            descs=self.descs,
            page_required=self.page_required,
            page=next_page,
            values=self.values,
            confirm_msg=self.confirm_msg,
            skip_msg=self.skip_msg,
            done_msg=self.done_msg,
            done_future=self.done_future,
        )
        await inter.response.send_modal(modal)
        await modal.wait()
        self.values.update(modal.values)
        if self.done_future and not self.done_future.done():
            self.done_future.set_result(self.values)
        self.stop()

    async def wait_until_done(self):
        """Wait for this modal to complete."""
        return await self.done_future


# ==================== WRAPPER FUNCTIONS ====================


def modal(
    title: str,
    pages: List[List],
    descs: List[str] = None,
    page_required: List[bool] = None,
    confirm_msg: Union[str, Callable] = None,
    skip_msg: str = None,
    done_msg: str = None,
) -> Modal:
    """
    Create a modal with optional page support.

    Args:
        title: Modal title
        pages: List of pages (each page is a list of fields)
        descs: Page descriptions for confirmation prompts
        page_required: List indicating if each page is required
        confirm_msg: Confirmation message template or function
        skip_msg: Message shown when skipping optional pages
        done_msg: Final completion message

    Returns:
        Modal instance ready to be displayed
    """
    return Modal(
        title=title,
        pages=pages,
        descs=descs,
        page_required=page_required,
        confirm_msg=confirm_msg,
        skip_msg=skip_msg,
        done_msg=done_msg,
    )


def simple_modal(
    title: str, fields: List, required: bool = True, done_msg: str = None
) -> Modal:
    """
    Create a simple single-page modal.

    Args:
        title: Modal title
        fields: List of fields for the single page
        required: Whether the page is required
        done_msg: Completion message
    """
    m = modal(title, [fields], page_required=[required], done_msg=done_msg)
    if not m.done_future.done():
        m.done_future.set_result(None)
    return m


# ==================== ADDITIONAL UTILITY FUNCTIONS ====================


def conf_add(server_id: int, keys: list, name: str, value: Any, comment: str = None):
    """
    Add a new configuration entry to a server-specific TOML configuration file.

    This function reads the current configuration for the specified server,
    creates any necessary intermediate tables if keys don't exist, adds a new
    key-value pair (with an optional comment), and writes the updated
    configuration back to the file.

    Args:
        server_id (int): The ID of the server for which to modify configuration.
        keys (list): Hierarchical keys representing the configuration section path.
                     Example: ['database', 'credentials'] for the [database.credentials] section.
        name (str): The name of the configuration key to add.
        value (Any): The value to assign to the configuration key. Must be a TOML-supported type.
        comment (str, optional): Comment to add above the configuration entry.
                                Defaults to None.

    Raises:
        FileNotFoundError: If the directory structure doesn't exist and cannot be created.
        PermissionError: If lacking write permissions for the configuration file.
        tomlkit.exceptions.TOMLKitError: If TOML parsing/serialization fails.

    Side Effects:
        - Modifies the server-specific TOML file on disk
        - Creates the file and any intermediate tables if they don't exist

    Example:
        >>> conf_add(12345, ['server'], 'host', 'localhost', 'Server hostname')
        # Creates/updates data/server-configs/12345.toml:
        # [server]
        # host = "localhost" # Server hostname

        >>> conf_add(12345, ['db', 'prod'], 'port', 5432)
        # Creates/updates data/server-configs/12345.toml:
        # [db.prod]
        # port = 5432
    """
    cDoc = conf_get(server_id=server_id)

    # Navigate to or create the nested structure
    current_level = cDoc
    for key in keys:
        if key not in current_level:
            current_level[key] = tk.table()
        current_level = current_level[key]

    # Add the key-value pair
    current_level[name] = value
    if comment is not None:
        current_level[name].comment(comment)

    directory = "data/server-configs"
    os.makedirs(directory, exist_ok=True)

    file_path = os.path.join(directory, f"{server_id}.toml")
    with open(file_path, "w") as f:
        f.write(tk.dumps(cDoc))


def conf_get(server_id: int, keys: list = None) -> Union[dict, Any]:
    """
    Retrieve configuration values from a server-specific TOML configuration file.

    This function reads the server-specific TOML file and returns either the entire
    configuration dictionary or a nested value specified by a sequence of keys.
    If the file doesn't exist, returns an empty document. If any keys in the path
    don't exist, returns an empty document for that section.

    Args:
        server_id (int): The ID of the server for which to read configuration.
        keys (list, optional): A list of keys representing the hierarchical path
            to the desired configuration value. If empty or None, returns the entire
            configuration. Defaults to None.

    Returns:
        Union[dict, Any]: The entire configuration dictionary if keys is empty/None,
            otherwise the value at the specified key path. Returns empty document
            or empty tables for non-existent paths.

    Raises:
        tomlkit.exceptions.ParseError: If the TOML file contains syntax errors.

    Example:
        Given a 12345.toml with content:
            [database]
            host = "localhost"
            port = 5432

        >>> conf_get(12345)
        {'database': {'host': 'localhost', 'port': 5432}}

        >>> conf_get(12345, ['database', 'host'])
        'localhost'

        >>> conf_get(12345, ['nonexistent', 'key'])
        # Returns an empty table

    Note:
        - The function expects server configs in 'data/server-configs/{server_id}.toml'
        - Returns empty documents/tables for non-existent files or keys rather than raising errors
    """
    if keys is None:
        keys = []

    try:
        with open(f"data/server-configs/{str(server_id)}.toml", "r") as f:
            cDoc = tk.parse(f.read())
    except FileNotFoundError:
        cDoc = tk.document()
        return cDoc

    # Navigate through keys, creating empty tables for non-existent keys
    current_level = cDoc
    for key in keys:
        if key in current_level:
            current_level = current_level[key]
        else:
            # Key doesn't exist, return empty table
            return tk.table()

    return current_level


def bot_conf_add(keys: list, name: str, value: Any, comment: str = None):
    """
    Add a new configuration entry to the main bot TOML configuration file.

    This function reads the current bot configuration, creates any necessary
    intermediate tables if keys don't exist, adds a new key-value pair
    (with an optional comment), and writes the updated configuration back to the file.

    Args:
        keys (list): Hierarchical keys representing the configuration section path.
                     Example: ['database', 'credentials'] for the [database.credentials] section.
        name (str): The name of the configuration key to add.
        value (Any): The value to assign to the configuration key. Must be a TOML-supported type.
        comment (str, optional): Comment to add above the configuration entry.
                                Defaults to None.

    Raises:
        FileNotFoundError: If the config.toml file does not exist when reading.
        PermissionError: If lacking write permissions for config.toml.
        tomlkit.exceptions.TOMLKitError: If TOML parsing/serialization fails.

    Side Effects:
        - Modifies the 'config.toml' file on disk
        - Creates the file and any intermediate tables if they don't exist

    Example:
        >>> bot_conf_add(['server'], 'host', 'localhost', 'Server hostname')
        # Creates/updates config.toml:
        # [server]
        # host = "localhost" # Server hostname

        >>> bot_conf_add(['db', 'prod'], 'port', 5432)
        # Creates/updates config.toml:
        # [db.prod]
        # port = 5432
    """
    cDoc = bot_conf_get()

    # Navigate to or create the nested structure
    current_level = cDoc
    for key in keys:
        if key not in current_level:
            current_level[key] = tk.table()
        current_level = current_level[key]

    # Add the key-value pair
    current_level[name] = value
    if comment is not None:
        current_level[name].comment(comment)

    with open("config.toml", "w") as f:
        f.write(tk.dumps(cDoc))


def bot_conf_get(keys: list = None) -> Union[dict, Any]:
    """
    Retrieve configuration values from the main bot TOML configuration file.

    This function reads the 'config.toml' file and returns either the entire
    configuration dictionary or a nested value specified by a sequence of keys.
    If the file doesn't exist, returns an empty document. If any keys in the path
    don't exist, returns an empty document for that section.

    Args:
        keys (list, optional): A list of keys representing the hierarchical path
            to the desired configuration value. If empty or None, returns the entire
            configuration. Defaults to None.

    Returns:
        Union[dict, Any]: The entire configuration dictionary if keys is empty/None,
            otherwise the value at the specified key path. Returns empty document
            or empty tables for non-existent paths.

    Raises:
        tomlkit.exceptions.ParseError: If the TOML file contains syntax errors.

    Example:
        Given a config.toml with content:
            [database]
            host = "localhost"
            port = 5432

            [api]
            endpoints = ["/v1/auth", "/v1/data"]

        >>> bot_conf_get()
        {'database': {'host': 'localhost', 'port': 5432}, 'api': {'endpoints': ['/v1/auth', '/v1/data']}}

        >>> bot_conf_get(['database', 'host'])
        'localhost'

        >>> bot_conf_get(['nonexistent', 'key'])
        # Returns an empty table

    Note:
        - The function expects 'config.toml' in the current working directory
        - Returns empty documents/tables for non-existent files or keys rather than raising errors
    """
    if keys is None:
        keys = []

    try:
        with open("config.toml", "r") as f:
            cDoc = tk.parse(f.read())
    except FileNotFoundError:
        cDoc = tk.document()
        return cDoc

    # Navigate through keys, creating empty tables for non-existent keys
    current_level = cDoc
    for key in keys:
        if key in current_level:
            current_level = current_level[key]
        else:
            # Key doesn't exist, return empty table
            return tk.table()

    return current_level


def get_all_cogs():
    """
    Discovers and returns a list of all Python files in the discordCogs directory
    and its subdirectories, formatted as importable module paths.
    This function recursively scans the `./discordCogs` directory for all `.py` files
    and converts their file paths into dot-separated module names suitable for
    dynamic importing. The relative path structure is preserved and converted to
    Python module notation.

    Returns:
        list[str]: A list of strings representing importable module paths for each
                  discovered cog. For example:
                  - `./discordCogs/music/player.py` becomes `'music.player'`
                  - `./discordCogs/admin.py` becomes `'admin'`

    Example:
        >>> get_all_cogs()
        ['music.player', 'admin.moderation', 'utility.help']

    Note:
        - Only files with `.py` extension are included
        - The base path `./discordCogs` is excluded from the module path
        - Directory separators (`/` or `\`) are converted to dots (`.`)
        - Files in subdirectories are represented with dotted notation
    """
    cog_list = [
        str(p.relative_to(Path("./discordCogs")).with_suffix("")).replace("/", ".")
        for p in Path("./discordCogs").rglob("*.py")
    ]
    return cog_list
