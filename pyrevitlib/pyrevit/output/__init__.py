"""Compatibility access to the runtime-owned output window."""

import os.path as op

from pyrevit import HOST_APP, DB
from pyrevit import framework
from pyrevit.coreutils import envvars
from pyrevit.coreutils import charts
from pyrevit.runtime.types import ScriptConsoleManager, ScriptOutput
from pyrevit.userconfig import user_config
from pyrevit.output import linkmaker
from pyrevit import coreutils


DEFAULT_STYLESHEET_NAME = 'outputstyles.css'


def docclosing_eventhandler(sender, args):
    """Close all output windows on document closing."""
    ScriptConsoleManager.CloseActiveOutputWindows()


def setup_output_closer():
    """Setup document closing event listener."""
    HOST_APP.app.DocumentClosing += \
        framework.EventHandler[DB.Events.DocumentClosingEventArgs](
            docclosing_eventhandler
            )


def set_stylesheet(stylesheet):
    """Set active CSS stylesheet used by output windows."""
    if op.isfile(stylesheet):
        envvars.set_pyrevit_env_var(envvars.OUTPUT_STYLESHEET_ENVVAR,
                                    stylesheet)


def get_stylesheet():
    """Return active CSS stylesheet used by output windows."""
    return envvars.get_pyrevit_env_var(envvars.OUTPUT_STYLESHEET_ENVVAR)


def get_default_stylesheet():
    """Return default CSS stylesheet used by output windows."""
    return op.join(op.dirname(__file__), DEFAULT_STYLESHEET_NAME)


def reset_stylesheet():
    """Reset active stylesheet to default."""
    envvars.set_pyrevit_env_var(envvars.OUTPUT_STYLESHEET_ENVVAR,
                                get_default_stylesheet())


active_stylesheet = user_config.output_stylesheet or get_default_stylesheet()
set_stylesheet(active_stylesheet)


class PyRevitOutputWindow(object):
    """Thin compatibility shim over ``ScriptOutput`` in the runtime."""

    def _runtime_output(self):
        return ScriptOutput.GetDefault()

    def __getattr__(self, name):
        return getattr(self._runtime_output(), name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return

        try:
            setattr(self._runtime_output(), name, value)
        except Exception:
            object.__setattr__(self, name, value)

    def close_others(self, all_open_outputs=False):
        return self._runtime_output().close_others(all_open_outputs)

    def inject_to_head(self, element_tag, element_contents, attribs=None):
        return self._runtime_output().inject_to_head(
            element_tag,
            element_contents,
            attribs
            )

    def inject_to_body(self, element_tag, element_contents, attribs=None):
        return self._runtime_output().inject_to_body(
            element_tag,
            element_contents,
            attribs
            )

    def inject_script(self, script_code, attribs=None, body=False):
        return self._runtime_output().inject_script(script_code, attribs, body)

    def add_style(self, style_code, attribs=None):
        return self._runtime_output().add_style(style_code, attribs)

    def print_table(self, table_data, columns=None, formats=None,
                    title='', last_line_style=''):
        return self._runtime_output().print_table(
            table_data,
            columns,
            formats,
            title,
            last_line_style
            )

    def print_html_table(self, table_data, columns=None, formats=None,
                         title='', last_line_style='', **kwargs):
        return self._runtime_output().print_html_table(
            table_data,
            columns,
            formats,
            title,
            last_line_style,
            kwargs.get('column_head_align_styles', None),
            kwargs.get('column_data_align_styles', None),
            kwargs.get('column_widths', None),
            kwargs.get('column_vertical_border_style', None),
            kwargs.get('table_width_style', None),
            kwargs.get('repeat_head_as_foot', False),
            kwargs.get('row_striping', True)
            )

    @staticmethod
    def linkify(element_ids, title=None):
        """Create clickable link for provided Revit element ids."""
        return coreutils.prepare_html_str(
            linkmaker.make_link(element_ids, contents=title)
            )

    def make_chart(self, version=None):
        return charts.PyRevitOutputChart(self, version=version)

    def make_line_chart(self, version=None):
        return charts.PyRevitOutputChart(
            self,
            chart_type=charts.LINE_CHART,
            version=version
            )

    def make_stacked_chart(self, version=None):
        chart = charts.PyRevitOutputChart(
            self,
            chart_type=charts.LINE_CHART,
            version=version
            )
        chart.options.scales = {'yAxes': [{'stacked': True, }]}
        return chart

    def make_bar_chart(self, version=None):
        return charts.PyRevitOutputChart(
            self,
            chart_type=charts.BAR_CHART,
            version=version
            )

    def make_radar_chart(self, version=None):
        return charts.PyRevitOutputChart(
            self,
            chart_type=charts.RADAR_CHART,
            version=version
            )

    def make_polar_chart(self, version=None):
        return charts.PyRevitOutputChart(
            self,
            chart_type=charts.POLAR_CHART,
            version=version
            )

    def make_pie_chart(self, version=None):
        return charts.PyRevitOutputChart(
            self,
            chart_type=charts.PIE_CHART,
            version=version
            )

    def make_doughnut_chart(self, version=None):
        return charts.PyRevitOutputChart(
            self,
            chart_type=charts.DOUGHNUT_CHART,
            version=version
            )

    def make_bubble_chart(self, version=None):
        return charts.PyRevitOutputChart(
            self,
            chart_type=charts.BUBBLE_CHART,
            version=version
            )


def get_output():
    """:obj:`pyrevit.output.PyRevitOutputWindow`: Return output window."""
    return PyRevitOutputWindow()
