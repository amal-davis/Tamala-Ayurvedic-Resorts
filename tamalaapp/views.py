from decimal import Decimal
from django.shortcuts import render
from django.shortcuts import render
import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from .models import *
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from urllib.parse import urlencode
from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Order, OrderItem
from django.core.exceptions import ValidationError
import paypalrestsdk
from django.conf import settings


def index(request):
    categories = Category.objects.all()
    page_obj = Product.objects.all().order_by('-created_at')[:4]
    product = ProductImage.objects.all
    return render (request,'home.html',{'categories':categories,'page_obj':page_obj,'product':product})

   

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    categories = Category.objects.all()
    
    # Fetch related products from the same category, excluding the current product
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id).order_by('-created_at')[:4]

    return render(request, 'product_detail.html', {
        'product': product,
        'categories': categories,
        'related_products': related_products
    })


def ex(request):
    return render (request,'example.html')

@login_required(login_url='signin')
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))  # Get quantity from form

    # Check if the product is already in the cart
    cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)

    if created:
        cart_item.quantity = quantity
    else:
        cart_item.quantity += quantity

    cart_item.save()

    messages.success(request, "Product added to your cart successfully!")
    return redirect('cart')  # Redirect to cart page or any other page



@login_required(login_url='signin')
def cart(request):
    # Check if the user is authenticated
    if not request.user.is_authenticated:
        return redirect('signin')  # Redirect to sign-in if the user is not authenticated
    
    # Fetch cart items for the authenticated user
    cart_items = Cart.objects.filter(user=request.user)
    
    # Calculate total amount including delivery charges
    total_amount = sum(item.total_price for item in cart_items)
    total_delivery_charge = sum(item.product.delivery_charge for item in cart_items)
    categories = Category.objects.all()

    context = {
        'cart_items': cart_items,
        'total_amount': total_amount,
        'total_delivery_charge': total_delivery_charge,
        'categories': categories
    }
    return render(request, 'cart.html', context)



def remove_cart_item(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        Cart.objects.filter(id=item_id, user=request.user).delete()

        # Recalculate the total amount including delivery charge
        cart_items = Cart.objects.filter(user=request.user)
        total_amount = sum(item.total_price for item in cart_items)

        return JsonResponse({
            'success': True,
            'total_amount': total_amount,
            'total_delivery_charge': sum(item.product.delivery_charge for item in cart_items),
            'item_count': cart_items.count(),
        })
    return JsonResponse({'success': False})



def update_cart_quantity(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        new_quantity = int(request.POST.get('quantity'))

        cart_item = Cart.objects.get(id=item_id)
        cart_item.update_quantity(new_quantity)

        # Recalculate the total amount
        cart_items = Cart.objects.filter(user=request.user)
        total_amount = sum(item.total_price for item in cart_items)

        return JsonResponse({
            'item_total_price': cart_item.total_price,
            'total_amount': total_amount,
        })



def contact(request):
    return render (request,'contact_us.html')



@login_required(login_url='signin')
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user)
    
    # Calculate the total amount and delivery charges
    total_amount = sum(item.total_price for item in cart_items)
    total_delivery_charge = sum(item.product.delivery_charge for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total_amount': total_amount,
        'total_delivery_charge': total_delivery_charge,
    }
    
    return render(request, 'checkout.html', context)


# PayPal SDK Configuration
paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,  # Sandbox or live
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET,
})



@login_required(login_url='signin')
def process_order(request):
    if request.method == 'POST':
        # Create customer
        customer = Customer.objects.create(
            first_name=request.POST['first_name'],
            last_name=request.POST['last_name'],
            country=request.POST['country'],
            address=request.POST['address'],
            city=request.POST['city'],
            phone=request.POST['phone'],
            email=request.POST['email']
        )

        # Fetch cart items and calculate totals
        cart_items = Cart.objects.filter(user=request.user)
        subtotal = sum(Decimal(item.product.discount_price) * Decimal(item.quantity) for item in cart_items)
        delivery_charge = sum(Decimal(item.product.delivery_charge) for item in cart_items)
        total_amount = subtotal + delivery_charge

        # Build item list for PayPal
        items = []
        for item in cart_items:
            items.append({
                "name": item.product.name,
                "sku": str(item.product.id),
                "price": f"{Decimal(item.product.discount_price):.2f}",
                "currency": "USD",
                "quantity": item.quantity
            })

        # Debugging: Ensure all amounts are correct
        print("Items:", items)
        print("Subtotal:", f"{Decimal(subtotal):.2f}")
        print("Shipping:", f"{Decimal(delivery_charge):.2f}")
        print("Total Amount:", f"{Decimal(total_amount):.2f}")

        # Create PayPal payment
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": request.build_absolute_uri('/payment-success/'),
                "cancel_url": request.build_absolute_uri('/payment-cancelled/')
            },
            "transactions": [{
                "item_list": {
                    "items": items
                },
                "amount": {
                    "total": f"{Decimal(total_amount):.2f}",
                    "currency": "USD",
                    "details": {
                        "subtotal": f"{Decimal(subtotal):.2f}",
                        "shipping": f"{Decimal(delivery_charge):.2f}"
                    }
                },
                "description": f"Order payment by {customer.first_name} {customer.last_name}"
            }]
        })

        if payment.create():
            for link in payment.links:
                if link.rel == "approval_url":
                    return redirect(link.href)
        else:
            # Log PayPal error for debugging
            print(payment.error)
            return HttpResponse("Payment creation failed. Please try again.")

    return redirect('cart')











@login_required(login_url='signin')
def payment_success(request):
    payment_id = request.GET.get('paymentId')
    payer_id = request.GET.get('PayerID')

    # Execute PayPal payment
    payment = paypalrestsdk.Payment.find(payment_id)
    if payment.execute({"payer_id": payer_id}):
        # Payment was successful
        # You can update the order status and clear the cart here
        messages.success(request, "Payment was successful!")
        return redirect('order_summary')  # Redirect to order summary or another page
    else:
        print(payment.error)  # Log the error
        messages.error(request, "Payment failed. Please try again.")
        return redirect('cart')




@login_required(login_url='signin')
def payment_cancelled(request):
    messages.error(request, "Payment was cancelled.")
    return redirect('cart')




@login_required(login_url='signin')
def orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Set up pagination
    paginator = Paginator(orders, 12)  # 12 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'order.html', {'page_obj': page_obj})


def about(request):
    return render (request,'about_us.html')


@login_required(login_url='signin')
def admin_page(request):
    return render(request,'admin.html')


def logout_view(request):
    logout(request)
    return redirect('index')

def signup_page(request):
    return render(request, 'sign_in.html')

def usercreate(request):
    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        username = request.POST['username']
        password = request.POST['password']
        cpassword = request.POST['cpassword']
        email = request.POST['email']
        phone_no = request.POST['phone']

        if password == cpassword:
            # Check if the username is already taken
            if User.objects.filter(username=username).exists():
                messages.info(request, 'This username is already taken. Please choose a different one.')
                return redirect('signup_page')
            else:
                # Create the user and profile
                user = User.objects.create_user(
                    first_name=first_name,
                    last_name=last_name,
                    username=username,
                    password=password,
                    email=email
                )
                user.save()

                user_profile = UserProfile.objects.create(
                    user=user,
                    phone_number=phone_no
                )
                user_profile.save()
                print('Succeed....')
        else:
            messages.info(request, 'Passwords do not match!')
            print('Passwords do not match')
            return redirect('signup_page')

        return redirect('login_page')
    else:
        return render(request, 'sign_in.html')
    
    


def login_page(request):
    return render(request,'login.html')





def signin(request):
    if request.method == 'POST':
        # Get the username (or email) and password from the request, with default values to avoid KeyError
        username = request.POST.get('username', '')  # Assuming 'username' is the email
        password = request.POST.get('password', '')

        # Authenticate the user with the provided credentials
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # User authenticated successfully
            login(request, user)  # Log in the user

            # Redirect based on user type
            if user.is_staff:
                return redirect('admin_page')  # Redirect admin users to the admin page
            else:
                return redirect('index')  # Redirect regular users to the index page
        else:
            # Authentication failed, show an error message
            messages.error(request, 'Invalid credentials. Please try again.')
            # Render the login page with the error message
            return render(request, 'login.html', context={'error': 'Invalid credentials'})

    # If not a POST request, render the login page
    return render(request, 'login.html')

def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        message = request.POST.get('message')

        if name and email and phone and message:
            # Save the contact form data to the database
            Contact.objects.create(name=name, email=email, phone=phone, message=message)
            messages.success(request, 'Thank you for your message. We will get back to you shortly.')
            return redirect('contact')
        else:
            messages.error(request, 'Please fill in all fields.')


    return render(request, 'contact_us.html')




def message_list_view(request):
    messages = Contact.objects.all()
    return render(request, 'contact_list.html', {'messages': messages})


def delete_message(request, pk):
    product_type = get_object_or_404(Contact, id=pk)
    
    product_type.delete()  # Delete the product type
    
    return redirect('message_list_view')  # Redirect to the list page




def add_category_view(request):
    if request.method == 'POST':
        
        name = request.POST.get('name')
        image = request.FILES.get('image')

        if name:
            Category.objects.create(name=name, image=image)
            return redirect('add_category_view')  # Redirect to clear the form

    categories = Category.objects.all()
    return render(request, 'add_category.html', {'categories': categories})




def edit_category_view(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        image = request.FILES.get('image')

        if name:
            category.name = name
            if image:
                category.image = image
            category.save()
            return redirect('add_category_view')

    return render(request, 'edit_category.html', {'category': category})




def delete_category(request, pk):
    product_type = get_object_or_404(Category, id=pk)
    
    product_type.delete()  # Delete the product type
    
    return redirect('add_category_view')  # Redirect to the list page



def category_products(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    sort_option = request.GET.get('sort', 'latest')

    if sort_option == 'low-to-high':
        products = Product.objects.filter(category=category).order_by('discount_price', 'price')
    elif sort_option == 'high-to-low':
        products = Product.objects.filter(category=category).order_by('-discount_price', '-price')
    elif sort_option == 'a-to-z':
        products = Product.objects.filter(category=category).order_by('heading')
    elif sort_option == 'z-to-a':
        products = Product.objects.filter(category=category).order_by('-heading')
    else:
        products = Product.objects.filter(category=category).order_by('-created_at')

    paginator = Paginator(products, 20)  # 20 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    categories = Category.objects.all()
    

    context = {
        'category': category,
        'page_obj': page_obj,
        'sort_option': sort_option,
        'categories':categories
    }
    return render(request, 'category.html', context)


def products(request):
    sort_option = request.GET.get('sort', 'latest')

    if sort_option == 'low-to-high':
        all_products = Product.objects.all().order_by('discount_price', 'price')
    elif sort_option == 'high-to-low':
        all_products = Product.objects.all().order_by('-discount_price', '-price')
    elif sort_option == 'a-to-z':
        all_products = Product.objects.all().order_by('heading')
    elif sort_option == 'z-to-a':
        all_products = Product.objects.all().order_by('-heading')
    else:
        all_products = Product.objects.all().order_by('-created_at')

    paginator = Paginator(all_products, 20)  # 20 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    categories = Category.objects.all()

    return render(request, 'product_page.html', {'page_obj': page_obj, 'sort_option': sort_option,'categories':categories})
# Create your views here.





def add_product(request):
    if request.method == 'POST':
        category_id = request.POST.get('category')
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        discount_price = request.POST.get('discount_price')
        stock = request.POST.get('stock')
        delivery_charge = request.POST.get('delivery_charge', 0.00)

        # Create product instance
        product = Product.objects.create(
            category_id=category_id,
            name=name,
            description=description,
            price=price,
            discount_price=discount_price,
            stock=stock,
            delivery_charge=delivery_charge
        )

        # Handle multiple images
        images = request.FILES.getlist('images')
        for image in images:
            ProductImage.objects.create(product=product, image=image)

        return redirect('add_product')
    else:
        categories = Category.objects.all()
        products = Product.objects.all()
        reversed_order = reversed(list(products))
        return render(request, 'add_products.html', {'categories': categories,'products': reversed_order,
 })


def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        product.category_id = request.POST.get('category', product.category_id)
        product.heading = request.POST.get('heading', product.heading)
        product.description = request.POST.get('description', product.description)
        product.price = float(request.POST.get('price', product.price))
        product.discount_price = float(request.POST.get('discount_price', product.discount_price))
        product.stock = int(request.POST.get('stock', product.stock))
        product.delivery_charge = float(request.POST.get('delivery_charge', product.delivery_charge))
        product.save()

        # Handle new images if updated
        new_images = request.FILES.getlist('images')
        for image in new_images:
            ProductImage.objects.create(product=product, image=image)

        return redirect('add_product')

    context = {
        'product': product,
        'categories': Category.objects.all(),
    }

    return render(request, 'edit_product.html', context)

def p_delete_form(request,pk):
    edit=Product.objects.get(id=pk)
    edit.delete()
    return redirect('add_product')


# Create your views here.


@login_required(login_url='signin')
def user_order(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Set up pagination
    paginator = Paginator(orders, 12)  # 12 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'order.html', {'page_obj': page_obj})


@login_required(login_url='signin')
def manage_orders(request):
    orders = Order.objects.all().order_by('-created_at')
    paginator = Paginator(orders, 12)  # Show 12 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'manage_orders.html', {'page_obj': page_obj})


@login_required(login_url='signin')
def update_order_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        order.status = request.POST['status']
        order.save()
        return redirect('manage_orders')


def search_results(request):
    query = request.GET.get('q')
    products = Product.objects.filter(name__icontains=query) if query else Product.objects.none()

    context = {
        'query': query,
        'products': products
    }
    return render(request, 'search_results.html', context)

# Create your views here.
