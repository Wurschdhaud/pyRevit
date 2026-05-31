from pyrevit import forms, script
from match import clipboard

logger = script.get_logger()

if not forms.is_registered_dockable_panel(clipboard.MatchHistoryClipboard):
    forms.register_dockable_panel(clipboard.MatchHistoryClipboard, default_visible=False)
else:
    logger.debug("Skipped registering dockable pane. Already exists.")
