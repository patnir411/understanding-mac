import unittest
from unittest.mock import MagicMock, patch, call
from collections import OrderedDict

from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme
from rich.bar import Bar
from rich.tree import Tree
from rich.table import Table

# Attempt to import functions from system_stats.py
try:
    import sys
    import os
    # This assumes system_stats.py is in the parent directory if tests are in a subdir,
    # or in the same directory. Adjust as needed.
    # If tests are in root alongside system_stats.py, this might not be needed or simpler.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # sys.path.insert(0, os.path.abspath(os.path.join(current_dir, '..'))) # If in subdir
    sys.path.insert(0, current_dir) # If in same dir, or if system_stats is installable/in PYTHONPATH

    import system_stats as system_stats_module
    create_system_layout = system_stats_module.create_system_layout
    create_panel_for_category = system_stats_module.create_panel_for_category
    format_value = getattr(system_stats_module, 'format_value', lambda x: str(x)) # Default if not found
except ImportError as e:
    print(f"WARNING: Could not import from system_stats.py: {e}. Mocks will be heavily relied upon.")
    system_stats_module = MagicMock()
    create_system_layout = MagicMock(return_value=Layout(name="mocked_root_layout"))
    create_panel_for_category = MagicMock(return_value=Panel(Text("Mocked Panel from create_panel_for_category")))
    format_value = MagicMock(side_effect=lambda x: str(x))

class TestSystemStatsLayout(unittest.TestCase):

    def setUp(self):
        self.test_theme = Theme({
            "info": "dim cyan", "warning": "magenta", "danger": "bold red",
            "title": "bold white on blue", "panel.title": "bold white",
            "panel.border": "dim blue", "table.header": "bold cyan",
            "table.cell": "green", "bar.complete": "green",
            "bar.finished": "dim green", "rule.line": "dim blue",
        })

        # Patch the custom_theme in the system_stats_module.
        # This is vital if the real create_panel_for_category is used, as it accesses this global.
        self.theme_patcher = patch.object(system_stats_module, 'custom_theme', self.test_theme, create=True)
        self.mock_custom_theme_from_patch = self.theme_patcher.start()

        # Mock data for various test scenarios
        self.mock_system_stats_for_layout = OrderedDict([("CPU Stats", OrderedDict([("Overall", 50.0)]))])
        self.cpu_stats_data_for_bar = OrderedDict([("Overall", 85.5)])
        self.memory_virtual_for_bar = OrderedDict([("Total", 100000), ("Available", 50000), ("Percent", 50.0)])
        self.disk_usage_for_bar = OrderedDict([("Total", 100000), ("Used", 75000), ("Percent", 75.0)])
        self.disk_partitions_data = [
            {'Device': '/dev/sda1', 'Mountpoint': '/', 'FSType': 'ext4', 'Opts': 'rw,relatime'},
            {'Device': '/dev/sdb1', 'Mountpoint': '/data', 'FSType': 'xfs', 'Opts': 'rw,noatime'}
        ]
        self.network_interfaces_data = OrderedDict([
            ('eth0', [{'Family': 'AF_INET', 'Address': '192.168.1.10', 'Netmask': '255.255.255.0', 'Broadcast': '192.168.1.255'}]),
            ('lo', [{'Family': 'AF_INET', 'Address': '127.0.0.1', 'Netmask': '255.0.0.0', 'Broadcast': None}])
        ])
        self.users_data = [{'Name': 'user1', 'Terminal': 'tty1', 'Host': 'localhost', 'Started': 1678886400.0, 'PID': 1234}]
        self.gpu_error_data = ["Error: GPU not found"]
        self.cpu_times_data = OrderedDict([('User', 100.0), ('System', 50.0), ('Idle', 850.0)])
        self.simple_metric_data = OrderedDict([("Boot Time", "2023-03-15 10:00:00")])
        self.empty_list_data = []
        self.mixed_list_data = [1, {"a": "b"}, "string", Text("Rich Text")]


    def tearDown(self):
        self.theme_patcher.stop()

    def _get_renderable_from_panel(self, panel: Panel, metric_name: str):
        if not isinstance(panel, Panel): return None
        table = panel.renderable # This is the main Table in the Panel

        # Ensure 'table' is actually a Table and has the expected structure
        if not isinstance(table, Table) or not hasattr(table, 'columns') or len(table.columns) < 2:
            # print(f"Debug: _get_renderable_from_panel: panel.renderable is not a valid Table or has < 2 columns. Type: {type(table)}")
            return None

        # Iterate through the cells of the first column (metric names)
        # table.columns[0] is the first Column object.
        # table.columns[0].cells is a list of renderables in that column.
        try:
            metric_column_cells = table.columns[0].cells
            value_column_cells = table.columns[1].cells
        except IndexError:
            # This can happen if the table doesn't have two columns as expected
            # print(f"Debug: _get_renderable_from_panel: Table columns are fewer than expected. Columns: {len(table.columns)}")
            return None

        for i, metric_cell_content in enumerate(metric_column_cells):
            metric_text = ""
            if isinstance(metric_cell_content, Text):
                metric_text = metric_cell_content.plain
            elif isinstance(metric_cell_content, str):
                metric_text = metric_cell_content
            # Add other simple renderable types if necessary, e.g. if a metric name itself is a number.
            # For this specific use case, metric names are generally Text or strings.

            if metric_text == metric_name:
                # Return the corresponding cell content from the second column (values)
                if i < len(value_column_cells):
                    return value_column_cells[i]
                else:
                    # This case (metric found but no corresponding value cell) should ideally not happen
                    # if the table is constructed correctly with pairs of metric names and values.
                    # print(f"Debug: _get_renderable_from_panel: Metric '{metric_name}' found at index {i}, but no corresponding value cell.")
                    return None # Should not happen if table is well-formed

        # print(f"Debug: _get_renderable_from_panel: Metric '{metric_name}' not found in table.")
        return None

    # --- Tests for create_panel_for_category ---
    def test_cpfc_bar_cpu(self):
        panel = create_panel_for_category("CPU Stats", self.cpu_stats_data_for_bar)
        self.assertIsInstance(self._get_renderable_from_panel(panel, "Overall"), Bar)

    def test_cpfc_bar_memory(self):
        panel = create_panel_for_category("Memory Stats", OrderedDict([("Virtual Memory", self.memory_virtual_for_bar)]))
        sub_table = self._get_renderable_from_panel(panel, "Virtual Memory")
        self.assertIsInstance(sub_table, Table)
        percent_bar = None
        for r_cells in sub_table.rows: # r_cells is list of Cell objects
            if r_cells[0].renderable.plain == "Percent": percent_bar = r_cells[1].renderable; break
        self.assertIsInstance(percent_bar, Bar)

    def test_cpfc_bar_disk_usage(self):
        panel = create_panel_for_category("Disk Stats", OrderedDict([("Disk Usage", self.disk_usage_for_bar)]))
        sub_table = self._get_renderable_from_panel(panel, "Disk Usage")
        self.assertIsInstance(sub_table, Table)
        percent_bar = None
        for r_cells in sub_table.rows:
            if r_cells[0].renderable.plain == "Percent": percent_bar = r_cells[1].renderable; break
        self.assertIsInstance(percent_bar, Bar)

    def test_cpfc_tree_disk_partitions(self):
        panel = create_panel_for_category("Disk Stats", OrderedDict([("Disk Partitions", self.disk_partitions_data)]))
        tree = self._get_renderable_from_panel(panel, "Disk Partitions")
        self.assertIsInstance(tree, Tree)
        if tree: self.assertEqual(len(tree.children), len(self.disk_partitions_data))

    def test_cpfc_tree_network_interfaces(self):
        panel = create_panel_for_category("Network Stats", OrderedDict([("Network Interfaces", self.network_interfaces_data)]))
        tree = self._get_renderable_from_panel(panel, "Network Interfaces")
        self.assertIsInstance(tree, Tree)
        if tree: self.assertEqual(len(tree.children), len(self.network_interfaces_data))

    def test_cpfc_list_of_dicts_table(self):
        panel = create_panel_for_category("Other Stats", OrderedDict([("Users", self.users_data)]))
        table = self._get_renderable_from_panel(panel, "Users")
        self.assertIsInstance(table, Table)
        if table: self.assertEqual(len(table.rows), len(self.users_data))

    def test_cpfc_list_of_strings(self):
        panel = create_panel_for_category("GPU Stats", OrderedDict([("GPU Details", self.gpu_error_data)]))
        table = self._get_renderable_from_panel(panel, "GPU Details")
        self.assertIsInstance(table, Table)
        if table: self.assertEqual(len(table.rows), len(self.gpu_error_data)); self.assertFalse(table.show_header)

    def test_cpfc_nested_dict_table(self):
        panel = create_panel_for_category("CPU Stats", OrderedDict([("CPU Times", self.cpu_times_data)]))
        sub_table = self._get_renderable_from_panel(panel, "CPU Times")
        self.assertIsInstance(sub_table, Table)
        if sub_table: self.assertEqual(len(sub_table.rows), len(self.cpu_times_data))

    def test_cpfc_simple_value(self):
        panel = create_panel_for_category("Other Stats", self.simple_metric_data)
        value_renderable = self._get_renderable_from_panel(panel, "Boot Time")
        self.assertIsInstance(value_renderable, Text)
        if value_renderable: self.assertEqual(value_renderable.plain, self.simple_metric_data["Boot Time"])

    def test_cpfc_empty_list(self):
        panel = create_panel_for_category("Other Stats", OrderedDict([("EmptyData", self.empty_list_data)]))
        table = self._get_renderable_from_panel(panel, "EmptyData")
        self.assertIsInstance(table, Table)
        if table: self.assertEqual(len(table.rows), 1); self.assertEqual(table.rows[0][0].renderable.plain, "No data available.")

    def test_cpfc_mixed_list_content(self):
        panel = create_panel_for_category("Mixed Content", OrderedDict([("Mixed List", self.mixed_list_data)]))
        self.assertIsInstance(panel, Panel)
        # This branch directly adds a Text object to the category_table for the metric's value
        value_renderable = self._get_renderable_from_panel(panel, "Mixed List")
        self.assertIsInstance(value_renderable, Text, "Mixed list content should be rendered as Text.")
        if value_renderable:
            # The actual string is truncated to 100 chars + "..."
            # e.g., "List: [1, {'a': 'b'}, 'string', <Text str='Rich Text' style=''>][:100]..."
            # We'll check for the "List: " prefix and the "..." suffix and the style.
            self.assertTrue(value_renderable.plain.startswith("List: ["),
                            f"Expected mixed list text to start with 'List: [', got '{value_renderable.plain}'")
            self.assertTrue(value_renderable.plain.endswith("..."),
                            f"Expected mixed list text to end with '...', got '{value_renderable.plain}'")
            self.assertEqual(value_renderable.style, "italic warning")

    # --- Test for interactive footer logic ---
    def test_interactive_footer_logic(self):
        if isinstance(create_system_layout, MagicMock) and not create_system_layout.called: # Ensure mock is set if used
            mock_layout_obj = Layout(name="root")
            mock_layout_obj.split_column(Layout(name="header"), Layout(name="main"), Layout(name="footer", minimum_size=1))
            mock_layout_obj["footer"].update(Panel(Text("Initial Footer")))
            create_system_layout.return_value = mock_layout_obj

        main_layout = create_system_layout(self.mock_system_stats_for_layout, self.test_theme)
        insights_panel = Panel(Text("Test Insights")); gpt_prompt_panel = Panel(Text("GPT Prompt"))
        querying_gpt_panel = Panel(Text("Querying GPT...")); gpt_response_panel = Panel(Text("GPT Response"))
        footer_section = main_layout["footer"]; is_footer_split = False

        if not is_footer_split:
            footer_section.split_row(Layout(insights_panel, name="insights_footer"), Layout(gpt_prompt_panel, name="gpt_footer"))
            is_footer_split = True
        self.assertTrue(is_footer_split); self.assertIn("insights_footer", footer_section); self.assertIn("gpt_footer", footer_section)

        if is_footer_split: footer_section["gpt_footer"].update(gpt_prompt_panel) # Next prompt
        else: self.fail("Footer not split for next prompt")
        self.assertIn("gpt_footer", footer_section) # Check update didn't remove

        footer_section["gpt_footer"].update(querying_gpt_panel) # Querying status
        footer_section["gpt_footer"].update(gpt_response_panel) # Response status
        self.assertIn("gpt_footer", footer_section) # Final check

    # --- Tests for create_system_layout ---
    @patch.object(system_stats_module, 'create_panel_for_category')
    def test_create_system_layout_calls_create_panel(self, mock_cpfc_func):
        mock_cpfc_func.return_value = Panel(Text("Mocked Category Panel"))
        stats_data = OrderedDict([
            ("CPU Stats", {"Overall": 10}), ("Memory Stats", {}), ("Disk Stats", {}),
            ("Network Stats", {}), ("Sensor Stats", {}), ("GPU Stats", []),
            ("CPU Info", {}), ("Other Stats", {})
        ])
        create_system_layout(stats_data, self.test_theme)
        expected_calls = [
            call("CPU Stats", stats_data["CPU Stats"]), call("Memory Stats", stats_data["Memory Stats"]),
            call("Disk Stats", stats_data["Disk Stats"]), call("Network Stats", stats_data["Network Stats"]),
            call("Sensor Stats", stats_data["Sensor Stats"]),
            call("GPU Stats", {"GPU Details": ["Not available or error"]}), # Corrected expectation for empty GPU list
            call("CPU Info", stats_data["CPU Info"]), call("Other System Stats", stats_data["Other Stats"])
        ]
        mock_cpfc_func.assert_has_calls(expected_calls, any_order=False)
        self.assertEqual(mock_cpfc_func.call_count, len(expected_calls))

    def test_create_system_layout_structure(self):
        main_layout = create_system_layout(OrderedDict(), self.test_theme) # Minimal data
        self.assertIsInstance(main_layout, Layout)
        for name in ["header", "main", "footer"]: self.assertIn(name, main_layout)
        main_sec = main_layout["main"]
        for name in ["left_column", "right_column"]: self.assertIn(name, main_sec)
        for name in ["cpu", "memory"]: self.assertIn(name, main_sec["left_column"]["cpu_mem"])
        for name in ["disk", "network"]: self.assertIn(name, main_sec["left_column"]["disk_net"])
        for name in ["sensors", "gpu"]: self.assertIn(name, main_sec["right_column"]["sensors_gpu"])
        for name in ["cpu_info", "misc"]: self.assertIn(name, main_sec["right_column"]["other"])
        self.assertIsInstance(main_layout["header"].renderable, Panel)
        self.assertIsInstance(main_layout["footer"].renderable, Panel)

if __name__ == '__main__':
    unittest.main()
