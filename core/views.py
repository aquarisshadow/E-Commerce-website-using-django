from django.shortcuts import render, get_object_or_404,redirect
from .models import Item,Order,OrderItem
from django.core.exceptions import ObjectDoesNotExist
from django.views.generic import ListView, DetailView,View
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.contrib import messages
from .forms import CheckOutForm


class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = "home.html"

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

        #form
        form = CheckOutForm()
        context = {
              'form':form
               }
        return render(self.request, 'checkout.html', context)

    def post(self, *args, **kwargs):
        form = CheckOutForm(self.request.POST or None)
        print(self.request.POST)
        if form.is_valid:

            print("Form is valid")
            return redirect('core:checkout')
        messages.warning(self.request, "Failed to Checkout")
        return redirect('core:checkout')



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





