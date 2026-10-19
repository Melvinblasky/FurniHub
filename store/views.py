from decimal import Decimal

from django.db.models import Avg, Count
from django.db import transaction, IntegrityError
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .models import (
    Category,
    Product,
    HeroBanner,
    Order,
    OrderItem,
    ContactMessage,
    Review,
    Wishlist,
)


# =========================
# HOME
# =========================

def home(request):

    hero = HeroBanner.objects.filter(
        active=True
    ).first()

    categories = Category.objects.all()

    products = Product.objects.filter(
        available=True,
        quantity__gt=0
    )[:8]

    context = {
        "hero": hero,
        "categories": categories,
        "products": products,
    }

    return render(
        request,
        "home.html",
        context
    )


# =========================
# SHOP
# =========================

def shop(request):
    products = Product.objects.filter(
        available=True,
        quantity__gt=0
    )

    categories = Category.objects.all()

    # Category filter
    category_slug = request.GET.get("category")

    if category_slug:
        products = products.filter(
            category__slug=category_slug
        )

    # Search
    search_query = request.GET.get("q")

    if search_query:
        products = products.filter(
            name__icontains=search_query
        )

    # Minimum price
    min_price = request.GET.get("min_price")

    if min_price:
        products = products.filter(
            price__gte=min_price
        )

    # Maximum price
    max_price = request.GET.get("max_price")

    if max_price:
        products = products.filter(
            price__lte=max_price
        )

    # Sorting
    sort = request.GET.get("sort")

    if sort == "price_low":
        products = products.order_by("price")

    elif sort == "price_high":
        products = products.order_by("-price")

    elif sort == "name":
        products = products.order_by("name")

    else:
        products = products.order_by("-created_at")

    context = {
        "products": products,
        "categories": categories,
        "active_category": category_slug,
        "search_query": search_query,
        "min_price": min_price,
        "max_price": max_price,
        "sort": sort,
    }

    return render(
        request,
        "shop.html",
        context
    )


# =========================
# PRODUCT DETAIL
# =========================

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    reviews = product.reviews.select_related("customer").all()

    rating_summary = reviews.aggregate(
        average_rating=Avg("rating"),
        review_count=Count("id")
    )

    user_review = None
    is_in_wishlist = False

    if request.user.is_authenticated:
        user_review = reviews.filter(
            customer=request.user
        ).first()

        is_in_wishlist = Wishlist.objects.filter(
            customer=request.user,
            product=product
        ).exists()

    context = {
        "product": product,
        "reviews": reviews,
        "average_rating": rating_summary["average_rating"],
        "review_count": rating_summary["review_count"],
        "user_review": user_review,
        "is_in_wishlist": is_in_wishlist,
    }

    return render(request, "product_detail.html", context)

@login_required(login_url="login")
def add_review(request, product_id):
    if request.method != "POST":
        return redirect("product_detail", product_id=product_id)

    product = get_object_or_404(
        Product,
        id=product_id
    )

    rating_value = request.POST.get("rating", "")
    comment = request.POST.get("comment", "").strip()

    try:
        rating = int(rating_value)
    except (ValueError, TypeError):
        messages.error(request, "Please select a valid star rating.")
        return redirect("product_detail", product_id=product.id)

    if rating < 1 or rating > 5:
        messages.error(request, "Your rating must be between 1 and 5 stars.")
        return redirect("product_detail", product_id=product.id)

    if not comment:
        messages.error(request, "Please write a comment for your review.")
        return redirect("product_detail", product_id=product.id)

    if Review.objects.filter(
        product=product,
        customer=request.user
    ).exists():
        messages.error(request, "You have already reviewed this product.")
        return redirect("product_detail", product_id=product.id)

    try:
        with transaction.atomic():
            Review.objects.create(
                product=product,
                customer=request.user,
                rating=rating,
                comment=comment
            )
    except IntegrityError:
        messages.error(request, "You have already reviewed this product.")
        return redirect("product_detail", product_id=product.id)

    messages.success(request, "Thank you! Your review has been submitted.")
    return redirect("product_detail", product_id=product.id)

# =========================
# ADD TO CART
# =========================

def add_to_cart(request, product_id):
    if request.method != "POST":
        return redirect("product_detail", product_id=product_id)

    product = get_object_or_404(
        Product,
        id=product_id,
        available=True,
        quantity__gt=0
    )

    try:
        quantity = int(request.POST.get("quantity", 1))
    except (ValueError, TypeError):
        return redirect("product_detail", product_id=product_id)

    if quantity < 1:
        return redirect("product_detail", product_id=product_id)

    cart = request.session.get("cart", {})
    product_id = str(product_id)

    try:
        current_quantity = int(cart.get(product_id, 0))
    except (ValueError, TypeError):
        current_quantity = 0

    new_quantity = min(
        current_quantity + quantity,
        product.quantity
    )

    cart[product_id] = new_quantity

    request.session["cart"] = cart
    request.session.modified = True

    return redirect("cart")


# =========================
# CART
# =========================

def cart(request):

    cart = request.session.get(
        "cart",
        {}
    )

    cart_items = []

    total = Decimal("0.00")

    for product_id, quantity in cart.items():

        product = get_object_or_404(
            Product,
            id=product_id
        )

        subtotal = (
            product.price * quantity
        )

        total += subtotal

        cart_items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal,
            "total": subtotal,
        })

    context = {
        "cart_items": cart_items,
        "total": total,
    }

    return render(
        request,
        "cart.html",
        context
    )


# =========================
# REMOVE FROM CART
# =========================

def remove_from_cart(
    request,
    product_id
):

    cart = request.session.get(
        "cart",
        {}
    )

    product_id = str(product_id)

    if product_id in cart:

        del cart[product_id]

    request.session["cart"] = cart
    request.session.modified = True

    return redirect("cart")


# =========================
# UPDATE CART
# =========================

def update_cart(request, product_id):
    if request.method != "POST":
        return redirect("cart")

    cart = request.session.get("cart", {})
    product_id = str(product_id)

    if product_id not in cart:
        return redirect("cart")

    product = get_object_or_404(
        Product,
        id=product_id
    )

    if not product.available or product.quantity <= 0:
        cart.pop(product_id, None)

    else:
        try:
            quantity = int(request.POST.get("quantity", 1))
        except (ValueError, TypeError):
            return redirect("cart")

        if quantity <= 0:
            cart.pop(product_id, None)
        else:
            cart[product_id] = min(
                quantity,
                product.quantity
            )

    request.session["cart"] = cart
    request.session.modified = True

    return redirect("cart")


# =========================
# CHECKOUT
# =========================

def checkout(request):
    cart = request.session.get("cart", {})

    if not cart:
        return redirect("cart")

    cart_items = []
    total = Decimal("0.00")

    # Validate the cart before displaying checkout.
    for product_id, quantity in cart.items():
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            return redirect("cart")

        product = get_object_or_404(
            Product,
            id=product_id
        )

        if (
            not product.available
            or product.quantity <= 0
            or quantity <= 0
            or quantity > product.quantity
        ):
            return redirect("cart")

        item_total = product.price * quantity
        total += item_total

        cart_items.append({
            "product": product,
            "quantity": quantity,
            "total": item_total,
        })

    # Place the order.
    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()

        # Make sure all checkout fields are provided.
        if not all([
            full_name,
            email,
            phone,
            address,
            city,
            state,
        ]):
            return render(
                request,
                "checkout.html",
                {
                    "cart_items": cart_items,
                    "total": total,
                    "error": "Please complete all checkout fields.",
                }
            )

        # Lock and recheck products before creating the order.
        from django.db import transaction

        with transaction.atomic():
            product_ids = [item["product"].id for item in cart_items]

            locked_products = Product.objects.select_for_update().filter(
                id__in=product_ids
            )

            products = {
                product.id: product
                for product in locked_products
            }

            # Revalidate stock in case it changed during checkout.
            for item in cart_items:
                product_id = item["product"].id
                quantity = item["quantity"]
                product = products.get(product_id)

                if (
                    product is None
                    or not product.available
                    or product.quantity < quantity
                    or quantity <= 0
                ):
                    return redirect("cart")

            # Recalculate the total using the locked products.
            total = sum(
                (
                    products[item["product"].id].price
                    * item["quantity"]
                    for item in cart_items
                ),
                Decimal("0.00")
            )

            order = Order.objects.create(
                customer=(
                    request.user
                    if request.user.is_authenticated
                    else None
                ),
                full_name=full_name,
                email=email,
                phone=phone,
                address=address,
                city=city,
                state=state,
                total_price=total,
            )

            # Create order items and reduce stock.
            for item in cart_items:
                product = products[item["product"].id]
                quantity = item["quantity"]

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.price,
                )

                product.quantity -= quantity

                if product.quantity == 0:
                    product.available = False

                product.save(
                    update_fields=["quantity", "available"]
                )

        # Clear the cart only after the order succeeds.
        request.session["cart"] = {}
        request.session.modified = True

        return redirect(
            "order_success",
            order_id=order.id
        )

    # Display the checkout page.
    return render(
        request,
        "checkout.html",
        {
            "cart_items": cart_items,
            "total": total,
        }
    )

# =========================
# ORDER SUCCESS
# =========================

def order_success(
    request,
    order_id
):

    order = get_object_or_404(
        Order,
        id=order_id
    )

    return render(
        request,
        "order_success.html",
        {
            "order": order
        }
    )


# =========================
# REGISTER
# =========================

def register(request):

    if request.user.is_authenticated:

        return redirect("home")

    if request.method == "POST":

        username = request.POST.get(
            "username"
        )

        email = request.POST.get(
            "email"
        )

        password = request.POST.get(
            "password"
        )

        confirm_password = request.POST.get(
            "confirm_password"
        )

        if password != confirm_password:

            return render(
                request,
                "register.html",
                {
                    "error": (
                        "Passwords do not match."
                    )
                }
            )

        if User.objects.filter(
            username=username
        ).exists():

            return render(
                request,
                "register.html",
                {
                    "error": (
                        "Username already exists."
                    )
                }
            )

        if User.objects.filter(
            email=email
        ).exists():

            return render(
                request,
                "register.html",
                {
                    "error": (
                        "Email already exists."
                    )
                }
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        login(
            request,
            user
        )

        return redirect("home")

    return render(
        request,
        "register.html"
    )


# =========================
# LOGIN
# =========================

def login_view(request):

    if request.user.is_authenticated:

        return redirect("home")

    if request.method == "POST":

        username = request.POST.get(
            "username"
        )

        password = request.POST.get(
            "password"
        )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(
                request,
                user
            )

            return redirect("home")

        return render(
            request,
            "login.html",
            {
                "error": (
                    "Invalid username "
                    "or password."
                )
            }
        )

    return render(
        request,
        "login.html"
    )


# =========================
# LOGOUT
# =========================

def logout_view(request):

    logout(request)

    return redirect("home")


# =========================
# ACCOUNT
# =========================

@login_required
def account(request):

    orders = Order.objects.filter(
        customer=request.user
    ).prefetch_related(
        "items"
    )

    return render(
        request,
        "account.html",
        {
            "orders": orders
        }
    )


# =========================
# CONTACT
# =========================

def contact(request):

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        subject = request.POST.get(
            "subject",
            ""
        ).strip()

        message = request.POST.get(
            "message",
            ""
        ).strip()

        if (
            not name
            or not email
            or not subject
            or not message
        ):

            return render(
                request,
                "contact.html",
                {
                    "error": (
                        "Please fill in all fields."
                    ),
                    "form_data": request.POST,
                }
            )

        ContactMessage.objects.create(

            name=name,

            email=email,

            subject=subject,

            message=message,
        )

        return render(
            request,
            "contact.html",
            {
                "success": (
                    "Thank you! Your message "
                    "has been sent successfully."
                )
            }
        )

    return render(
        request,
        "contact.html"
    )


# =========================
# CATEGORIES
# =========================

def categories(request):

    return render(
        request,
        "categories.html"
    )


# =========================
# ABOUT
# =========================

def about(request):

    return render(
        request,
        "about.html"
    )


# =========================
# CONTACT
# =========================

def contact(request):

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        subject = request.POST.get(
            "subject",
            ""
        ).strip()

        message = request.POST.get(
            "message",
            ""
        ).strip()

        if (
            not name
            or not email
            or not subject
            or not message
        ):

            return render(
                request,
                "contact.html",
                {
                    "error": "Please fill in all fields.",
                    "form_data": request.POST,
                }
            )

        ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message,
        )

        return render(
            request,
            "contact.html",
            {
                "success": (
                    "Thank you! Your message "
                    "has been sent successfully."
                )
            }
        )

    return render(
        request,
        "contact.html"
    )

@login_required(login_url="login")
def add_to_wishlist(request, product_id):
    if request.method != "POST":
        return redirect("product_detail", product_id=product_id)

    product = get_object_or_404(Product, id=product_id)

    wishlist_item, created = Wishlist.objects.get_or_create(
        customer=request.user,
        product=product
    )

    if created:
        messages.success(
            request,
            f"{product.name} has been added to your wishlist."
        )
    else:
        messages.info(
            request,
            f"{product.name} is already in your wishlist."
        )

    return redirect(request.POST.get("next") or "wishlist")


@login_required(login_url="login")
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(
        customer=request.user
    ).select_related("product", "product__category")

    context = {
        "wishlist_items": wishlist_items,
    }

    return render(request, "wishlist.html", context)


@login_required(login_url="login")
def remove_from_wishlist(request, product_id):
    if request.method != "POST":
        return redirect("wishlist")

    Wishlist.objects.filter(
        customer=request.user,
        product_id=product_id
    ).delete()

    messages.success(request, "Product removed from your wishlist.")

    return redirect("wishlist")