"""Evaluator-only fixtures: never pass these trigger paths to the investigator."""
import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.browser


def open_cart(page, live_server):
    page.goto(live_server)
    page.get_by_role('button', name='Your bag').click()


def apply_coupon(page, value='SAVE10'):
    page.get_by_role('textbox', name='Have a little something?').fill(value)
    page.get_by_role('button', name='Apply', exact=True).click()


def test_seeded_defect_is_real_and_checkout_completes(page, live_server, tmp_path):
    open_cart(page, live_server)
    apply_coupon(page)
    expect(page.get_by_test_id('total')).to_have_text('$90.00')
    page.get_by_role('button', name='Continue to review').click()
    # The first hypothesis, ordinary address entry, does NOT lose the coupon.
    expect(page.get_by_test_id('total')).to_have_text('$90.00')
    expect(page.get_by_role('button', name='Apply', exact=True)).to_be_hidden()
    expect(page.locator('#coupon')).to_be_hidden()
    page.get_by_role('button', name='Edit address', exact=True).click()
    expect(page.get_by_role('button', name='Apply', exact=True)).to_be_visible()
    page.get_by_role('textbox', name='Street address', exact=True).fill('200 Pine Street')
    page.get_by_role('button', name='Save address').click()
    # Reproduction assertion passes because we observed the intentional defect.
    expect(page.get_by_test_id('total')).to_have_text('$100.00')
    expect(page.locator('#discount-row')).to_be_hidden()
    expect(page.get_by_role('button', name='Apply', exact=True)).to_be_hidden()
    expect(page.locator('#coupon')).to_be_hidden()
    page.screenshot(path=str(tmp_path / 'actual-discount-loss.png'))
    page.get_by_role('button', name='Place demo order').click()
    expect(page.get_by_text("You're going places.", exact=True)).to_be_visible()
    expect(page.locator('#order-total')).to_have_text('Demo total: $100.00')


def test_ineligible_coupon_is_correct_behavior_and_preserves_valid_coupon(page, live_server):
    open_cart(page, live_server)
    apply_coupon(page, 'VIP20')
    expect(page.get_by_role('status')).to_contain_text('not eligible')
    expect(page.get_by_test_id('total')).to_have_text('$100.00')
    apply_coupon(page)
    apply_coupon(page, 'VIP20')
    expect(page.get_by_test_id('total')).to_have_text('$90.00')
    page.get_by_label('Quantity', exact=True).select_option('2')
    expect(page.get_by_test_id('total')).to_have_text('$180.00')


def test_fresh_context_and_reset_restore_fixtures(page, live_server, browser):
    open_cart(page, live_server)
    apply_coupon(page)
    page.reload()
    page.get_by_role('button', name='Your bag').click()
    expect(page.get_by_test_id('total')).to_have_text('$90.00')
    with browser.new_context() as fresh:
        other = fresh.new_page()
        open_cart(other, live_server)
        expect(other.get_by_test_id('total')).to_have_text('$100.00')
    page.get_by_role('button', name='Reset demo session').click()
    expect(page.get_by_test_id('total')).to_have_text('$100.00')
    expect(page.get_by_role('textbox', name='Street address', exact=True)).to_have_value('100 Market Street')


def test_report_from_checkout_creates_honest_receipt_with_safe_text(page, live_server):
    open_cart(page, live_server)
    page.get_by_role('dialog', name='Your next adventure.').get_by_role(
        'button', name='Report a problem ↗', exact=True).click()
    complaint = 'Discount vanished <img src=x onerror=alert(1)>'
    page.get_by_label('What happened?', exact=True).fill(complaint)
    page.get_by_label('What did you expect?', exact=True).fill('Keep the valid SAVE10 discount.')
    page.get_by_role('button', name='Submit report').click()
    page.wait_for_url('**/cases/*')
    expect(page.get_by_role('heading', name='Your report is in.', exact=True)).to_be_visible()
    expect(page.locator('#complaint')).to_have_text(complaint)
    assert page.locator('#complaint img').count() == 0
    expect(page.locator('#case-message')).to_contain_text('disabled')
    page.reload()
    expect(page.locator('#complaint')).to_have_text(complaint)


def test_mobile_layout_and_report_button(page, live_server):
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(live_server)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.get_by_role('button', name='Report a problem ↗', exact=True).click()
    expect(page.get_by_role('heading', name='Tell us what happened.')).to_be_visible()
