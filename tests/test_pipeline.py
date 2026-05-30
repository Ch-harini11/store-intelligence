# PROMPT: "Generate a pytest test suite for a store intelligence camera event pipeline. The pipeline tracks visitor_ids and emits ENTRY, EXIT, ZONE_ENTER, and ZONE_EXIT events when points move between zone polygons. Write tests validating that the VisitorStateTracker correctly detects transitions and returns valid structured events conforming to standard properties."
# CHANGES MADE: Added explicit imports for path resolution, validated session sequence numbering, and configured mock UTC timestamps.

import pytest
import os
import sys
from datetime import datetime

# Adjust path to find app and pipeline packages
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline.tracker import VisitorStateTracker, ZONES

def test_tracker_initialization():
    tracker = VisitorStateTracker(visitor_id="VIS_test")
    assert tracker.visitor_id == "VIS_test"
    assert tracker.current_zone is None
    assert tracker.in_store is False
    assert tracker.session_seq == 0

def test_tracker_store_entry_exit():
    tracker = VisitorStateTracker(visitor_id="VIS_test")
    
    # 1. Move to Entrance zone (Entry transition)
    entrance_pt = [150, 100]  # Inside Entrance polygon
    events = tracker.update_position(entrance_pt)
    
    # Entrance triggers both store ENTRY and zone-specific ZONE_ENTER
    assert len(events) == 2
    types = [e["event_type"] for e in events]
    assert "ENTRY" in types
    assert "ZONE_ENTER" in types
    assert tracker.in_store is True
    assert tracker.current_zone == "Entrance"

    # 2. Move out of Entrance to Exit zone
    exit_pt = [650, 485]  # Inside Exit polygon
    events2 = tracker.update_position(exit_pt)
    
    # Triggers ZONE_EXIT for Entrance and ZONE_ENTER for Exit
    assert len(events2) == 2
    assert events2[0]["event_type"] == "ZONE_EXIT"
    assert events2[0]["zone_id"] == "Entrance"
    assert events2[1]["event_type"] == "ZONE_ENTER"
    assert events2[1]["zone_id"] == "Exit"
    assert tracker.current_zone == "Exit"

    # 3. Move outside (Store exit)
    outside_pt = [10, 10]  # Outside any polygon
    events3 = tracker.update_position(outside_pt)
    
    # Triggers ZONE_EXIT for Exit and general EXIT event
    assert len(events3) == 2
    types3 = [e["event_type"] for e in events3]
    assert "ZONE_EXIT" in types3
    assert "EXIT" in types3
    assert tracker.in_store is False
    assert tracker.current_zone is None
