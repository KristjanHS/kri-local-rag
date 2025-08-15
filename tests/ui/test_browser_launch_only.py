from __future__ import annotations

from playwright.sync_api import Page, expect

pytestmark = []


def test_browser_launch_smoke(page: Page) -> None:
    page.set_content("<h1 id='ok'>OK</h1>")
    expect(page.locator("#ok")).to_be_visible(timeout=10000)
