from django.urls import path
from  tamalaapp import views


urlpatterns = [    
    
    path('',views.index,name='index'),
    path('products',views.products,name='products'),
    path('product_detail/<slug:slug>/',views.product_detail,name='product_detail'),
    path('checkout',views.checkout,name='checkout'),
    path('add_to_cart/<int:product_id>/',views.add_to_cart,name='add_to_cart'),
    path('cart/',views.cart,name='cart'),
    path('update_cart_quantity',views.update_cart_quantity,name='update_cart_quantity'),
    path('remove_cart_item',views.remove_cart_item,name='remove_cart_item'),
    path('ex',views.ex,name='ex'),
    path('category_products/<int:category_id>/',views.category_products,name='category_products'),
    path('contact',views.contact,name='contact'),
    path('user_order',views.user_order,name=' user_order'),
    path('about',views.about,name='about'),
    path('admin_page',views.admin_page,name='admin_page'),
    path('logout_view',views.logout_view,name='logout_view'),
    path('signin',views.signin,name='signin'),
    path('signup_page',views.signup_page,name='signup_page'),
    path('usercreate',views.usercreate,name='usercreate'),
    path('login_page',views.login_page,name='login_page'),
    path('message_list_view',views.message_list_view,name='message_list_view'),
    path('delete_message/<int:pk>/',views.delete_message,name='delete_message'),
    path('contact_view',views.contact_view,name='contact_view'),
    path('add_category_view',views.add_category_view,name='add_category_view'),
    path('edit_category_view/<int:category_id>/',views.edit_category_view,name='edit_category_view'),
    path('delete_category/<int:pk>/',views.delete_category,name='delete_category'),
    path('add_product',views.add_product,name='add_product'),
    path('edit_product/<int:product_id>/',views.edit_product,name='edit_product'),
    path('p_delete_form/<int:pk>/',views.p_delete_form,name='p_delete_form'),
    path('process_order',views.process_order,name='process_order'),
    path('search_results',views.search_results,name='search_results'),
    path('manage_orders',views.manage_orders,name='manage_orders'),
    path('orders',views.orders,name='orders'),
    path('update_order_status/<int:order_id>/',views.update_order_status,name='update_order_status'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-cancelled/', views.payment_cancelled, name='payment_cancelled'),

]
