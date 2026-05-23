from pyrevit._perf import mark as _perfmark, time_block as _perfblock
_perfmark("startup.pyRevitTools:entry")

from pyrevit import forms, script
_perfmark("startup.pyRevitTools:after `from pyrevit import forms, script`")

from match import panel
_perfmark("startup.pyRevitTools:after `from match import panel`")

logger = script.get_logger()

if not forms.is_registered_dockable_panel(panel.MatchHistoryClipboard):
    with _perfblock("startup.pyRevitTools:register_dockable_panel(MatchHistoryClipboard)"):
        forms.register_dockable_panel(panel.MatchHistoryClipboard, default_visible=False)
else:
    logger.debug("Skipped registering dockable pane. Already exists.")

_perfmark("startup.pyRevitTools:exit")
