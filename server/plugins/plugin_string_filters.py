# Manages string filters.

import json
import logging

from nicegui import APIRouter, ui, app
from fastapi.responses import FileResponse

import theme
from string_filters import StringFilter, StringFilterManager  # noqa: F401
from plugin_base import PluginBase, MenuItem

# Logger config
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)

# Device routes
router = APIRouter(tags=["string_filters"])
ROUTE_STRING_FILTERS = "/subject_filters"
ROUTE_STRING_FILTER_DOWNOLOAD = "/subject_filters_download"

# Menu(s)
menu = MenuItem("Event Subject Filters", ROUTE_STRING_FILTERS)
menu.sort_order = 11

# Plugin
plugin = PluginBase()
plugin += menu


@router.page(ROUTE_STRING_FILTERS, favicon=theme.PAGE_ICON)
async def subject_filter_manager():
    # Get list of filters.
    fm = app.string_filter_manager
    filter_dicts = [dict(filt) for filt in fm.filters]

    # TODO: Support filter testing on the page.
    # TODO: Add buttons to move filter up and down in the list.

    # TODO: NiceGUI Pandas example using ui.grid looks way better.
    # https://github.com/zauberzeug/nicegui/blob/main/examples/pandas_dataframe/main.py
    # Also "table and slots"
    # https://github.com/zauberzeug/nicegui/blob/main/examples/table_and_slots/main.py
    # Pull in header & select tab header for current page
    with theme.header():
        ui.markdown("### Event Subject Filters")
        grid = None  # Forward declaration

        with ui.row():

            async def button_add(event):
                filt = StringFilter(regexp="<NO MATCH>", replacement="")
                fm = app.string_filter_manager
                fm += filt
                fm.save()

                # Update the grid
                filter_dicts = [dict(filt) for filt in fm.filters]
                grid.options["rowData"] = filter_dicts
                grid.update()

            async def button_delete(event):
                row = await grid.get_selected_row()
                if not row:
                    logger.debug("Filter delete: No row selected.")

                filter = StringFilter(**row)
                fm = app.string_filter_manager
                fm -= filter
                fm.save()

                # Update the grid
                filter_dicts = [dict(filt) for filt in fm.filters]
                grid.options["rowData"] = filter_dicts
                grid.update()

            async def button_delete_all(event):
                fm = app.string_filter_manager

                # Update data
                fm.clear()
                fm.save()

                # Update UI
                grid.options["rowData"] = None
                grid.update()

            # Filter Editing Dialog
            # Forward declarations
            dialog = None
            field_regex = None
            field_replacement = None

            async def button_edit_save(event):
                # Original filter
                row = await grid.get_selected_row()
                filter_orig = StringFilter(**row)
                print(filter_orig)

                # New Filter
                filter_new = StringFilter(
                    regexp=field_regex.value, replacement=field_replacement.value
                )
                print(filter_new)

                # Update the filter.
                # Filter manager will raise an exception if the filter is not found.
                try:
                    fm = app.string_filter_manager
                    fm.replace(filter_orig, filter_new)
                    fm.save()

                except:  # noqa: E722
                    pass

                # Update the grid
                filter_dicts = [dict(filt) for filt in fm.filters]
                grid.options["rowData"] = filter_dicts
                grid.update()

                dialog.close()

            # Dialog for editing.
            with ui.dialog() as dialog, ui.card():
                field_regex = ui.input(label="Match", placeholder="regex")
                field_replacement = ui.input(
                    label="Replacement", placeholder="new string"
                )

                with ui.row():
                    ui.button("Save", on_click=button_edit_save)
                    ui.button("Cancel", on_click=dialog.close)

            async def dialog_update():
                # Update Dialog fields
                row = await grid.get_selected_row()
                if not row:
                    logger.debug("Filter delete: No row selected.")
                    return

                field_regex.value = row["regexp"]
                field_replacement.value = row["replacement"]

                # Open
                dialog.open()

            ui.button("Add", icon="add_circle", on_click=button_add)
            ui.button("Edit", icon="edit", on_click=dialog_update)
            ui.button("Delete", icon="delete_forever", on_click=button_delete)
            ui.button("Delete All", icon="delete_forever", on_click=button_delete_all)
            # ui.button("Test", icon="play_circle")

        # Grid
        grid = ui.aggrid(
            {
                "columnDefs": [
                    {
                        "headerName": "Regular Expression",
                        "field": "regexp",
                        "sortable": "true",
                    },
                    {
                        "headerName": "Replacement",
                        "field": "replacement",
                        "sortable": "true",
                    },
                ],
                "rowData": filter_dicts,
                "rowSelection": "single",
            }
        )

        # File Download/Upload Buttons
        with ui.row():

            async def button_download(event):
                ui.navigate.to(ROUTE_STRING_FILTER_DOWNOLOAD)

            async def file_upload(event):
                # Attempt to read in file.
                with event.content as fp:
                    data = json.load(fp)
                    logger.debug(f"File upload: {data}")

                fm = app.string_filter_manager
                for filter in data:
                    fm += StringFilter(**filter)
                fm.save()

                # Update the grid
                filter_dicts = [dict(filt) for filt in fm.filters]
                grid.options["rowData"] = filter_dicts
                grid.update()

            ui.button("Download", icon="download", on_click=button_download)
            ui.upload(label="UPLOAD", on_upload=file_upload, auto_upload=True)


@router.get(ROUTE_STRING_FILTER_DOWNOLOAD)
async def string_filters_get():
    fm = app.string_filter_manager
    logger.debug(f"Downloading filters: {fm.filename}")
    return FileResponse(
        fm.filename,
        media_type="text/json",
        filename="string-filters.json",
    )
