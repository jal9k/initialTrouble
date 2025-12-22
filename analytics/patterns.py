"""Pattern analysis utilities for issue categorization and resolution paths."""

from collections import Counter
from typing import Any

from .models import IssueCategory, Session, ToolEvent
from .storage import AnalyticsStorage


class PatternAnalyzer:
    """Analyze diagnostic patterns from analytics data."""

    # Tool to OSI layer mapping
    TOOL_OSI_LAYERS: dict[str, int] = {
        # Layer 1 - Physical
        "check_adapter_status": 1,
        "enable_wifi": 1,
        
        # Layer 2 - Data Link  
        "get_mac_address": 2,
        
        # Layer 3 - Network
        "get_ip_config": 3,
        "ping_gateway": 3,
        "ping_dns": 3,
        
        # Layer 4 - Transport (if we add port checking)
        "check_ports": 4,
        
        # Layer 7 - Application
        "test_dns_resolution": 7,
        "check_connectivity": 7,
        "test_http": 7,
    }

    # Tool to issue category mapping
    TOOL_CATEGORIES: dict[str, IssueCategory] = {
        "enable_wifi": IssueCategory.WIFI,
        "check_wifi_networks": IssueCategory.WIFI,
        "connect_wifi": IssueCategory.WIFI,
        "test_dns_resolution": IssueCategory.DNS,
        "configure_dns": IssueCategory.DNS,
        "ping_gateway": IssueCategory.GATEWAY,
        "ping_dns": IssueCategory.CONNECTIVITY,
        "check_connectivity": IssueCategory.CONNECTIVITY,
        "get_ip_config": IssueCategory.IP_CONFIG,
        "configure_ip": IssueCategory.IP_CONFIG,
        "check_adapter_status": IssueCategory.ADAPTER,
        "enable_adapter": IssueCategory.ADAPTER,
    }

    # Keywords for issue categorization from user messages
    CATEGORY_KEYWORDS: dict[IssueCategory, list[str]] = {
        IssueCategory.WIFI: ["wifi", "wireless", "wi-fi", "wlan", "ssid", "network name"],
        IssueCategory.DNS: ["dns", "domain", "resolve", "lookup", "name server"],
        IssueCategory.GATEWAY: ["gateway", "router", "default route", "hop"],
        IssueCategory.CONNECTIVITY: ["internet", "connection", "online", "offline", "ping"],
        IssueCategory.IP_CONFIG: ["ip address", "dhcp", "subnet", "netmask", "ipconfig"],
        IssueCategory.ADAPTER: ["adapter", "interface", "nic", "ethernet", "network card"],
    }

    def __init__(self, storage: AnalyticsStorage):
        """Initialize the pattern analyzer."""
        self.storage = storage

    def categorize_by_tools(self, tools_used: list[str]) -> IssueCategory:
        """Categorize issue based on tools used."""
        if not tools_used:
            return IssueCategory.UNKNOWN

        # Count categories from tools
        category_counts: Counter[IssueCategory] = Counter()
        
        for tool in tools_used:
            if tool in self.TOOL_CATEGORIES:
                category_counts[self.TOOL_CATEGORIES[tool]] += 1
        
        if not category_counts:
            return IssueCategory.OTHER
        
        # Return most common category
        return category_counts.most_common(1)[0][0]

    def categorize_by_keywords(self, text: str) -> IssueCategory:
        """Categorize issue based on keywords in text."""
        text_lower = text.lower()
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return category
        
        return IssueCategory.UNKNOWN

    def get_osi_layer(self, tools_used: list[str]) -> int | None:
        """Determine the OSI layer where issue was found/resolved."""
        if not tools_used:
            return None
        
        layers = []
        for tool in tools_used:
            if tool in self.TOOL_OSI_LAYERS:
                layers.append(self.TOOL_OSI_LAYERS[tool])
        
        if not layers:
            return None
        
        # Return lowest layer (issues are typically found bottom-up)
        return min(layers)

    def analyze_resolution_path(
        self,
        tool_sequence: list[str],
    ) -> dict[str, Any]:
        """Analyze a resolution path for patterns."""
        if not tool_sequence:
            return {
                "length": 0,
                "unique_tools": 0,
                "has_loops": False,
                "osi_layers_touched": [],
                "primary_category": IssueCategory.UNKNOWN.value,
            }

        # Check for loops (same tool called consecutively)
        loops = []
        for i in range(1, len(tool_sequence)):
            if tool_sequence[i] == tool_sequence[i-1]:
                loops.append(tool_sequence[i])

        # Get OSI layers
        layers = []
        for tool in tool_sequence:
            if tool in self.TOOL_OSI_LAYERS:
                layer = self.TOOL_OSI_LAYERS[tool]
                if layer not in layers:
                    layers.append(layer)

        return {
            "length": len(tool_sequence),
            "unique_tools": len(set(tool_sequence)),
            "has_loops": len(loops) > 0,
            "loop_count": len(loops),
            "looped_tools": list(set(loops)),
            "osi_layers_touched": sorted(layers),
            "followed_osi_order": layers == sorted(layers),
            "primary_category": self.categorize_by_tools(tool_sequence).value,
        }

    def get_common_patterns(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get the most common resolution patterns."""
        paths = self.storage.get_resolution_paths(successful_only=True, limit=1000)
        
        # Group by tool sequence
        sequence_counts: Counter[tuple[str, ...]] = Counter()
        for path in paths:
            sequence_counts[tuple(path.tool_sequence)] += 1
        
        # Analyze top patterns
        patterns = []
        for sequence, count in sequence_counts.most_common(limit):
            analysis = self.analyze_resolution_path(list(sequence))
            analysis["sequence"] = list(sequence)
            analysis["occurrence_count"] = count
            patterns.append(analysis)
        
        return patterns

    def get_category_stats(self) -> dict[str, Any]:
        """Get statistics by issue category."""
        breakdown = self.storage.get_issue_category_breakdown()
        total = sum(breakdown.values())
        
        stats = {}
        for category, count in breakdown.items():
            percentage = (count / total * 100) if total > 0 else 0
            stats[category] = {
                "count": count,
                "percentage": round(percentage, 2),
            }
        
        return {
            "total_sessions": total,
            "categories": stats,
        }

    def get_osi_layer_stats(self) -> dict[str, Any]:
        """Get statistics by OSI layer where issues were resolved."""
        sessions = self.storage.get_sessions(limit=10000)
        
        layer_counts: Counter[int] = Counter()
        for session in sessions:
            if session.osi_layer_resolved:
                layer_counts[session.osi_layer_resolved] += 1
        
        layer_names = {
            1: "Physical",
            2: "Data Link",
            3: "Network",
            4: "Transport",
            5: "Session",
            6: "Presentation",
            7: "Application",
        }
        
        total = sum(layer_counts.values())
        stats = {}
        for layer in range(1, 8):
            count = layer_counts.get(layer, 0)
            percentage = (count / total * 100) if total > 0 else 0
            stats[f"layer_{layer}"] = {
                "name": layer_names[layer],
                "count": count,
                "percentage": round(percentage, 2),
            }
        
        return {
            "total_with_layer": total,
            "layers": stats,
        }

    def detect_problematic_tools(self) -> list[dict[str, Any]]:
        """Detect tools that frequently fail or cause loops."""
        tool_stats = self.storage.get_tool_stats()
        
        problematic = []
        for stat in tool_stats:
            issues = []
            
            # High failure rate (>20%)
            if stat.total_calls >= 5 and stat.success_rate < 80:
                issues.append(f"High failure rate: {100 - stat.success_rate:.1f}%")
            
            # Frequently causes loops
            if stat.loop_occurrences > 0:
                loop_rate = (stat.loop_occurrences / stat.total_calls) * 100
                if loop_rate > 10:
                    issues.append(f"Causes loops: {loop_rate:.1f}% of calls")
            
            # Very slow execution
            if stat.avg_execution_time_ms > 5000:
                issues.append(f"Slow execution: {stat.avg_execution_time_ms:.0f}ms avg")
            
            if issues:
                problematic.append({
                    "tool_name": stat.tool_name,
                    "total_calls": stat.total_calls,
                    "success_rate": stat.success_rate,
                    "issues": issues,
                })
        
        return problematic

    def suggest_optimizations(self) -> list[str]:
        """Generate optimization suggestions based on patterns."""
        suggestions = []
        
        # Check for problematic tools
        problematic = self.detect_problematic_tools()
        for tool in problematic:
            for issue in tool["issues"]:
                suggestions.append(
                    f"Tool '{tool['tool_name']}': {issue}"
                )
        
        # Check common patterns for inefficiencies
        patterns = self.get_common_patterns(limit=5)
        for pattern in patterns:
            if pattern["has_loops"]:
                suggestions.append(
                    f"Common path has loops in: {', '.join(pattern['looped_tools'])}"
                )
            if not pattern["followed_osi_order"]:
                suggestions.append(
                    f"Common path doesn't follow OSI order: {pattern['sequence']}"
                )
        
        # Check quality metrics
        quality = self.storage.get_quality_metrics()
        if quality.drop_off_rate > 30:
            suggestions.append(
                f"High drop-off rate: {quality.drop_off_rate:.1f}% of sessions abandoned"
            )
        if quality.avg_messages_to_resolution > 10:
            suggestions.append(
                f"High message count to resolution: {quality.avg_messages_to_resolution:.1f} avg"
            )
        
        return suggestions


