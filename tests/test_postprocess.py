#!/usr/bin/env python3
"""Tests for postprocess.py pipeline."""
import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open
import sys
sys.path.append(str(Path(__file__).parent.parent))

from postprocess import (
    fix_metadata_from_filepath,
    fix_station_no_from_filepath,
    dedup_records,
    fix_total_votes,
    fix_remaining_ballots,
    fix_negative_values,
    flag_turnout,
    run_pipeline
)


class TestPostprocess:
    """Test cases for postprocessing functions."""

    def test_fix_metadata_from_filepath(self):
        """Test R0a: metadata extraction from filepath."""
        records = [
            {'file_path': '/chaiyaphum/1/001.pdf'},
            {'file_path': '/tak/2/002.pdf', 'province': 'existing'}
        ]
        result = fix_metadata_from_filepath(records, 'test_province')
        assert result[0]['province'] == 'test_province'
        assert result[0]['constituency'] == 'unknown'
        assert result[1]['province'] == 'existing'  # Should not override

    def test_dedup_records(self):
        """Test R0c: exact duplicate removal."""
        records = [
            {'id': 1, 'value': 'a'},
            {'id': 1, 'value': 'a'},  # duplicate
            {'id': 2, 'value': 'b'}
        ]
        result = dedup_records(records)
        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[1]['id'] == 2

    def test_fix_total_votes(self):
        """Test R3: total votes calculation."""
        records = [
            {'candidate_votes': {'A': 10, 'B': 20}},
            {'candidate_votes': {'C': 5}}
        ]
        result = fix_total_votes(records)
        assert result[0]['total_votes'] == 30
        assert result[1]['total_votes'] == 5

    def test_fix_remaining_ballots(self):
        """Test R4: remaining ballots calculation."""
        records = [
            {'registered_voters': 100, 'valid_ballots': 80},
            {'registered_voters': 50, 'valid_ballots': 60}  # invalid case
        ]
        result = fix_remaining_ballots(records)
        assert result[0]['remaining_ballots'] == 20
        assert result[1]['remaining_ballots'] == -10  # negative allowed here

    def test_fix_negative_values(self):
        """Test R5: negative value correction."""
        records = [
            {'remaining_ballots': -5, 'invalid_ballots': 2},
            {'remaining_ballots': 10, 'invalid_ballots': -1}
        ]
        result = fix_negative_values(records)
        assert result[0]['remaining_ballots'] == 0
        assert result[0]['invalid_ballots'] == 2
        assert result[1]['remaining_ballots'] == 10
        assert result[1]['invalid_ballots'] == 0

    def test_flag_turnout(self):
        """Test R8: turnout anomaly flagging."""
        records = [
            {'turnout_percentage': 95},
            {'turnout_percentage': 105},
            {'turnout_percentage': 85}
        ]
        result = flag_turnout(records)
        assert 'turnout_flag' not in result[0]
        assert result[1]['turnout_flag'] is True
        assert 'turnout_flag' not in result[2]

    @patch('postprocess.load_ocr_data')
    @patch('postprocess.load_killernay_data')
    @patch('postprocess.load_ect_reference')
    @patch('postprocess.save_json')
    def test_run_pipeline_dry_run(self, mock_save, mock_ect, mock_killernay, mock_load):
        """Test pipeline execution in dry run mode."""
        mock_load.return_value = [{'id': 1}]
        mock_killernay.return_value = {}
        mock_ect.return_value = {}

        stats = run_pipeline('test_province', dry_run=True)

        assert stats['province'] == 'test_province'
        assert stats['dry_run'] is True
        assert 'R0a' in stats['rules_applied']
        # save_json should be called for stats but not for records in dry run
        assert mock_save.call_count == 1  # only stats