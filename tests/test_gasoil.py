# -*- coding: utf-8 -*-
"""Test module for relperm"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np

from hypothesis import given, settings
import hypothesis.strategies as st

from test_wateroil import float_df_checker

from pyscal import GasOil


def check_table(df):
    """Check sanity of important columns"""
    assert not df.empty
    assert not df.isnull().values.any()
    assert len(df["sg"].unique()) == len(df)
    assert df["sg"].is_monotonic
    assert (df["sg"] >= 0.0).all()
    assert df["sgn"].is_monotonic
    assert df["son"].is_monotonic_decreasing
    assert df["krog"].is_monotonic_decreasing
    assert df["krg"].is_monotonic
    if "pc" in df:
        assert df["pc"].is_monotonic


def test_gasoil_init():
    """Check the __init__ method for GasOil

    are arguments handled correctly?"""
    gasoil = GasOil()
    assert isinstance(gasoil, GasOil)
    assert gasoil.swirr == 0.0
    assert gasoil.swl == 0.0
    assert gasoil.krgendanchor == ""  # Because sorg is zero

    gasoil = GasOil(swl=0.1)
    assert gasoil.swirr == 0.0
    assert gasoil.swl == 0.1

    gasoil = GasOil(swirr=0.1)
    assert gasoil.swirr == 0.1
    assert gasoil.swl == 0.1  # This one is zero by default, but will follow swirr.
    assert gasoil.sorg == 0.0
    assert gasoil.sgcr == 0.0

    gasoil = GasOil(tag="foobar")
    assert gasoil.tag == "foobar"

    # This will print a warning, but will be the same as ""
    gasoil = GasOil(krgendanchor="bogus")
    assert isinstance(gasoil, GasOil)
    assert gasoil.krgendanchor == ""

    # Test with h=1
    go = GasOil(h=1)
    go.add_corey_gas()
    go.add_corey_oil()
    assert np.isclose(go.crosspoint(), 0.5)
    assert len(go.table) == 2

    go = GasOil(swl=0.1, h=1)
    go.add_corey_gas()
    go.add_corey_oil()
    assert len(go.table) == 2
    assert np.isclose(go.crosspoint(), 0.45)
    assert np.isclose(go.table["sg"].min(), 0)
    assert np.isclose(go.table["sg"].max(), 0.9)


@settings(max_examples=500)
@given(
    st.floats(min_value=0, max_value=0.15),  # swl
    st.floats(min_value=0, max_value=0.3),  # sgcr
    st.floats(min_value=0, max_value=0.05),  # sorg
    st.floats(min_value=0.0001, max_value=0.2),  # h
    st.text(),
)
def test_gasoil_normalization(swl, sgcr, sorg, h, tag):
    """Check that normalization (sgn and son) is correct
    for all possible saturation endpoints"""
    go = GasOil(
        swirr=0.0, swl=swl, sgcr=sgcr, sorg=sorg, h=h, krgendanchor="sorg", tag=tag
    )
    assert not go.table.empty
    assert not go.table.isnull().values.any()

    # Check that son is 1 at sgcr
    assert float_df_checker(go.table, "sg", go.sgcr, "son", 1)

    # Check that son is 0 at sorg with this krgendanchor
    assert float_df_checker(go.table, "sg", 1 - go.sorg - go.swl, "son", 0)

    # Check that sgn is 0 at sgcr
    assert float_df_checker(go.table, "sg", go.sgcr, "sgn", 0)

    # Check that sgn is 1 at sorg
    assert float_df_checker(go.table, "sg", 1 - go.sorg - go.swl, "sgn", 1)

    # Redo with different krgendanchor
    go = GasOil(
        swirr=0.0, swl=swl, sgcr=sgcr, sorg=sorg, h=h, krgendanchor="", tag=tag
    )
    assert float_df_checker(go.table, "sg", 1 - go.swl, "sgn", 1)
    assert float_df_checker(go.table, "sg", go.sgcr, "sgn", 0)


def test_gasoil_krgendanchor():
    """Test behaviour of the krgendanchor"""
    gasoil = GasOil(krgendanchor="sorg", sorg=0.2, h=0.1)
    assert gasoil.sorg
    gasoil.add_corey_gas(ng=1)
    gasoil.add_corey_oil(nog=1)

    # kg should be 1.0 at 1 - sorg due to krgendanchor == "sorg":
    assert (
        gasoil.table[np.isclose(gasoil.table["sg"], 1 - gasoil.sorg)]["krg"].values[0]
        == 1.0
    )
    assert gasoil.table[np.isclose(gasoil.table["sg"], 1.0)]["krg"].values[0] == 1.0

    gasoil = GasOil(krgendanchor="", sorg=0.2, h=0.1)
    assert gasoil.sorg
    gasoil.add_corey_gas(ng=1)
    gasoil.add_corey_oil(nog=1)

    # kg should be < 1 at 1 - sorg due to krgendanchor being ""
    assert (
        gasoil.table[np.isclose(gasoil.table["sg"], 1 - gasoil.sorg)]["krg"].values[0]
        < 1.0
    )
    assert gasoil.table[np.isclose(gasoil.table["sg"], 1.0)]["krg"].values[0] == 1.0
    assert gasoil.selfcheck()

    # Test once more for LET curves:
    gasoil = GasOil(krgendanchor="sorg", sorg=0.2, h=0.1)
    assert gasoil.sorg
    gasoil.add_LET_gas(1, 1, 1)
    gasoil.add_LET_oil(1, 1, 1)

    # kg should be 1.0 at 1 - sorg due to krgendanchor == "sorg":
    assert (
        gasoil.table[np.isclose(gasoil.table["sg"], 1 - gasoil.sorg)]["krg"].values[0]
        == 1.0
    )
    assert gasoil.table[np.isclose(gasoil.table["sg"], 1.0)]["krg"].values[0] == 1.0

    gasoil = GasOil(krgendanchor="", sorg=0.2, h=0.1)
    assert gasoil.sorg
    gasoil.add_LET_gas(1, 1, 1)
    gasoil.add_LET_oil(1, 1, 1)
    assert gasoil.selfcheck()

    # kg should be < 1 at 1 - sorg due to krgendanchor being ""
    assert (
        gasoil.table[np.isclose(gasoil.table["sg"], 1 - gasoil.sorg)]["krg"].values[0]
        < 1.0
    )
    assert gasoil.table[np.isclose(gasoil.table["sg"], 1.0)]["krg"].values[0] == 1.0


def test_kromaxend():
    """Manual testing of kromax and kroend behaviour"""
    gasoil = GasOil(swirr=0.01, sgcr=0.01, h=0.01, swl=0.1, sorg=0.05)
    gasoil.add_LET_gas()
    gasoil.add_LET_oil(2, 2, 2)
    assert gasoil.table["krog"].max() == 1
    gasoil.add_LET_oil(2, 2, 2, 0.5, 0.9)
    assert gasoil.table["krog"].max() == 0.9
    # Second krog-value should be kroend, values in between will be linearly
    # interpolated in Eclipse
    assert gasoil.table.sort_values("krog")[-2:-1]["krog"].values[0] == 0.5

    gasoil.add_corey_oil(2)
    assert gasoil.table["krog"].max() == 1
    gasoil.add_corey_oil(2, 0.5, 0.9)
    assert gasoil.table["krog"].max() == 0.9
    assert gasoil.table.sort_values("krog")[-2:-1]["krog"].values[0] == 0.5


@settings(deadline=1000)
@given(st.floats(), st.floats())
def test_gasoil_corey1(ng, nog):
    go = GasOil()
    try:
        go.add_corey_oil(nog=nog)
        go.add_corey_gas(ng=ng)
    except AssertionError:
        # This happens for "invalid" input
        return

    assert "krog" in go.table
    assert "krg" in go.table
    assert isinstance(go.krgcomment, str)
    check_table(go.table)
    sgofstr = go.SGOF()
    assert len(sgofstr) > 100


@settings(deadline=1000)
@given(st.floats(), st.floats(), st.floats(), st.floats(), st.floats())
def test_gasoil_let1(l, e, t, krgend, krgmax):
    go = GasOil()
    try:
        go.add_LET_oil(l, e, t, krgend)
        go.add_LET_gas(l, e, t, krgend, krgmax)
    except AssertionError:
        # This happens for negative values f.ex.
        return
    assert "krog" in go.table
    assert "krg" in go.table
    assert isinstance(go.krgcomment, str)
    check_table(go.table)
    sgofstr = go.SGOF()
    assert len(sgofstr) > 100
