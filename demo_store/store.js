/* Original seeded demo target. Investigation agents must not read target source
 * or evaluation fixtures during black-box exploration. */
const checkout = document.querySelector('#checkout-dialog');
const addressForm = document.querySelector('#address-form');
const reviewPanel = document.querySelector('#review-panel');
const successPanel = document.querySelector('#success-panel');
const storageKey = 'field-demo-cart-v1';
const freshCart = () => ({ quantity: 1, coupon: null, address: null, stage: 'address', editingFromReview: false });
let cart = freshCart();
try {
  const saved = JSON.parse(localStorage.getItem(storageKey));
  if (saved && [1,2,3].includes(saved.quantity) && [null,'SAVE10'].includes(saved.coupon)) {
    cart = {...freshCart(), ...saved, stage:'address', editingFromReview:false};
  }
} catch { /* Browser storage may be unavailable; checkout still works. */ }
const money = value => new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(value);
const subtotal = () => 100 * cart.quantity;
const discount = () => cart.coupon === 'SAVE10' ? subtotal() * .1 : 0;
function saveCart() { try { localStorage.setItem(storageKey, JSON.stringify(cart)); } catch {} }
function render() {
  document.querySelector('#bag-count').textContent = cart.quantity;
  document.querySelector('#quantity').value = cart.quantity;
  document.querySelector('#line-price').textContent = money(subtotal());
  document.querySelector('#subtotal').textContent = money(subtotal());
  document.querySelector('#discount-row').hidden = !discount();
  document.querySelector('#discount').textContent = '−' + money(discount());
  document.querySelector('#coupon-label').textContent = cart.coupon || '';
  document.querySelector('#total').textContent = money(subtotal()-discount());
  addressForm.hidden = cart.stage !== 'address';
  reviewPanel.hidden = cart.stage !== 'review';
  successPanel.hidden = cart.stage !== 'success';
  document.querySelector('#step-address').classList.toggle('active',cart.stage === 'address');
  document.querySelector('#step-review').classList.toggle('active',cart.stage !== 'address');
  document.querySelector('#continue-review').firstChild.textContent = cart.editingFromReview ? 'Save address ' : 'Continue to review ';
  if (cart.address) document.querySelector('#address-summary').textContent = `${cart.address.full_name}\n${cart.address.street}\n${cart.address.city}, ${cart.address.postal_code}\nUnited States`;
  saveCart();
}
function openCheckout() { render(); checkout.showModal(); }
document.querySelector('#open-cart').addEventListener('click',openCheckout);
document.querySelector('#shop-button').addEventListener('click',openCheckout);
document.querySelector('#close-checkout').addEventListener('click',()=>checkout.close());
document.querySelector('#quantity').addEventListener('change', event => { cart.quantity=Number(event.target.value); render(); });
document.querySelector('#coupon-form').addEventListener('submit', event => {
  event.preventDefault();
  const code=document.querySelector('#coupon').value.trim().toUpperCase();
  const message=document.querySelector('#coupon-message');
  if (code==='SAVE10') { cart.coupon=code; message.textContent='SAVE10 applied. A little more room to roam.'; message.className='coupon-success'; }
  else { message.textContent=code==='VIP20' ? 'VIP20 is for members only. This demo guest cart is not eligible.' : 'That code is not valid. Try SAVE10.'; message.className='coupon-error'; }
  render();
});
addressForm.addEventListener('submit',event=>{
  event.preventDefault();
  cart.address=Object.fromEntries(new FormData(addressForm));
  // Seeded defect: returning from review rebuilds checkout state and drops coupon.
  // Initial address entry preserves it. This is observable business state loss.
  if (cart.editingFromReview) { cart.coupon=null; document.querySelector('#coupon-message').textContent=''; }
  cart.editingFromReview=false;
  cart.stage='review';
  render();
});
document.querySelector('#edit-address').addEventListener('click',()=>{ cart.editingFromReview=true; cart.stage='address'; render(); });
document.querySelector('#place-order').addEventListener('click',()=>{ cart.stage='success'; document.querySelector('#order-total').textContent=`Demo total: ${money(subtotal()-discount())}`; render(); });
function resetStore() {
  cart=freshCart(); addressForm.reset(); document.querySelector('#coupon-form').reset();
  document.querySelector('#coupon-message').textContent=''; render();
}
document.querySelector('#reset-store').addEventListener('click',resetStore);
document.querySelector('#finish-order').addEventListener('click',()=>{checkout.close();resetStore();});
render();
