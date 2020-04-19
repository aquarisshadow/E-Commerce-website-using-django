from django.shortcuts import render, get_object_or_404,redirect
from .models import Item, Order, OrderItem, Address, Payment, Coupon, Refund
from django.core.exceptions import ObjectDoesNotExist
from django.views.generic import ListView, DetailView,View
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.contrib import messages
from .forms import CheckOutForm, CouponForm, RefundForm
from django.conf import settings
import stripe
import string
import random

stripe.api_key = settings.STRIPE_SECRET_KEY

class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = "home.html"


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args,**kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
        except ObjectDoesNotExist:
            messages.error(self.request,"You don't have a active order")
            return redirect('/')
        context = {
            'object' : order
        }
        return render(self.request, "order_summary.html", context)


class ItemDetailView(DetailView):
    model = Item
    template_name = "product.html"

class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckOutForm()
            context = {
                'form': form,
                'couponform': CouponForm(),
                'order': order,
                'DISPLAY_COUPON_FORM': False
            }
            return render(self.request, 'checkout.html', context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have a Order")
            return redirect('core:checkout')

    def post(self, *args, **kwargs):
        form = CheckOutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                street_address = form.cleaned_data.get('street_address')
                apartment_address = form.cleaned_data.get('apartment_address')
                country = form.cleaned_data.get('country')
                zip = form.cleaned_data.get('zip')
               #TODO
               ##same_shipping_address = form.cleaned_data.get('same_shipping_address')
                #save_info = form.cleaned_data.get('save_info')
                payment_option = form.cleaned_data.get('payment_option')
                billing_address = Address(
                    user=self.request.user,
                    street_address=street_address,
                    apartment_address=apartment_address,
                    country=country,
                    zip=zip,
                    address_type='B'
                )
                billing_address.save()
                order.billing_address= billing_address
                order.save()
                if payment_option =='s':
                    return redirect('core:payment', payment_option='stripe')
                elif payment_option =='p':
                    return redirect('core:payment', payment_option='paypal')
                else:
                    messages.warning(self.request, "Invalid payment option selected")
                    return redirect('core:checkout')

        except ObjectDoesNotExist:
            messages.error(self.request,"You don't have a active order")
            return redirect('core:order-summary')

class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                'order':order,
                'DISPLAY_COUPON_FORM':False
                }
            return render(self.request, 'payment.html', context)
        else:
            messages.error(self.request, "Please add billing address")
            return redirect('core:checkout')

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered = False)
        token = self.request.POST.get('StripeToken')
        amount = int(order.get_total() * 100)  # value is in cents


        try:
            charge = stripe.Charge.create(
                amount=amount,  # value is in cents
                currency='usd',
                source=token
            )
            order.ordered = True
            # create payment object to store for future
            payment = Payment()
            order.ref_code = create_ref_code()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount= order.get_total()
            payment.save()

            #assign payment to order
            order_items = order.items.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()
            order.ordered = True
            order.payment=payment
            order.save()
            messages.warning(self.request, "Your Order was successful")
            return redirect("/")

        except stripe.error.CardError as e:
                body = e.json_body
                err = body.get('error', {})
                messages.warning(self.request, f"{err.get('message')}")
                return redirect("/")
        except stripe.error.RateLimitError as e:
                # Too many requests made to the API too quickly
                messages.warning(self.request, "Rate limit error")
                return redirect("/")

        except stripe.error.InvalidRequestError as e:
                # Invalid parameters were supplied to Stripe's API
                print(e)
                messages.warning(self.request, "Invalid parameters")
                return redirect("/")

        except stripe.error.AuthenticationError as e:
                # Authentication with Stripe's API failed
                # (maybe you changed API keys recently)
                messages.warning(self.request, "Not authenticated")
                return redirect("/")

        except stripe.error.APIConnectionError as e:
                # Network communication with Stripe failed
                messages.warning(self.request, "Network error")
                return redirect("/")

        except stripe.error.StripeError as e:
                # Display a very generic error to the user, and maybe send
                # yourself an email
                messages.warning(
                    self.request, "Something went wrong. You were not charged. Please try again.")
                return redirect("/")

        except Exception as e:
                # send an email to ourselves
                messages.warning(
                    self.request, "A serious error occurred. We have been notifed.")
                return redirect("/")







@login_required
def add_to_cart(request,slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
                            item=item,
                            user=request.user,
                            ordered=False)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        #check for existing item in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This Item quantity was updated")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This Item was added to your cart")
            order.items.add(order_item)
            return redirect("core:order-summary")
    else:
        ordered_date=timezone.now()
        order = Order.objects.create(user=request.user,ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This Item was added to your cart")
    return redirect("core:order-summary")

@login_required
def remove_from_cart(request, slug):
      item = get_object_or_404(Item, slug=slug)
      order_qs = Order.objects.filter(user=request.user, ordered=False)
      if order_qs.exists():
          order = order_qs[0]
            # check for existing item in the order
          if order.items.filter(item__slug=item.slug).exists():
             order_item = OrderItem.objects.filter(item=item, user=request.user,ordered=False)[0]
             order.items.remove(order_item)
             messages.info(request, "This Item was removed")
             return redirect("core:order-summary")
          else:
              messages.info(request, "This Item was not in your cart")
              return redirect("core:product", slug=slug)

      else:
          messages.info(request, "You do not have an active order")
          return redirect("core:product", slug=slug)
      return redirect("core:product", slug=slug)

@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)

def get_coupon(request, code):
    try:
        coupon= Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")
        return redirect("core:checkout")
class AddCouponView(View):
       def Post(self, *args, **kwargs):
           form = CouponForm(self.request.POST or None)
           if form.is_valid():
                try:
                    order = Order.objects.get(user=self.request.user, ordered=False)
                    code = form.cleaned_data.get('code')
                    order.coupon = get_coupon(self.request,code)
                    order.save()
                    messages.success(self.request, "coupon added successfully")
                    return redirect("core:checkout")
                except ObjectDoesNotExist:
                    messages.info(self.request, "")
                    return redirect('core:checkout')

class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form':form
        }
        return render(self.request, 'request_refund.html',context)
    def Post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message =form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested=True
                order.save()

                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()
                messages.info(self.request,"Your refund was done")
                return redirect('core:request-refund')
            except ObjectDoesNotExist:
                messages.info(self.request, "Your Order does not exits")
                return redirect('core:request-refund')









