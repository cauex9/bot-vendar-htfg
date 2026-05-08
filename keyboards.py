from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import database as db

def main_menu_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("💳 Comprar CC", callback_data="cat_2"))
    markup.add(
        InlineKeyboardButton("👤 Minha conta", callback_data="profile"),
        InlineKeyboardButton("💰 Adicionar saldo", callback_data="add_balance")
    )
    markup.add(
        InlineKeyboardButton("👑 Dono", callback_data="support")
    )
    return markup

def categories_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    categories = db.get_categories()
    for cat_id, cat_name in categories:
        markup.add(InlineKeyboardButton(cat_name, callback_data=f"cat_{cat_id}"))
    markup.add(InlineKeyboardButton("🔙 Voltar", callback_data="main_menu"))
    return markup

def products_keyboard(category_id: int):
    markup = InlineKeyboardMarkup(row_width=1)
    products = db.get_products_by_category(category_id)
    for prod_id, prod_name, prod_price in products:
        markup.add(InlineKeyboardButton(f"{prod_name} - R$ {prod_price:.2f}", callback_data=f"prod_{prod_id}"))
    markup.add(InlineKeyboardButton("🔙 Voltar", callback_data="shop"))
    return markup

def product_detail_keyboard(product_id: int, user_id: int):
    markup = InlineKeyboardMarkup(row_width=1)
    
    product = db.get_product(product_id)
    user = db.get_user(user_id)
    
    if product and user:
        price = product[4]
        balance = user[2]
        if balance >= price:
            markup.add(InlineKeyboardButton(f"💰 Pagar com Saldo (R$ {price:.2f})", callback_data=f"paybal_{product_id}"))
    
    markup.add(
        InlineKeyboardButton("⚡ Gerar Pix (Copia e Cola)", callback_data=f"buy_{product_id}"),
        InlineKeyboardButton("🔙 Voltar", callback_data="shop")
    )
    return markup

def profile_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📜 Histórico", callback_data="history"),
        InlineKeyboardButton("👥 Afiliados", callback_data="affiliates")
    )
    markup.add(
        InlineKeyboardButton("🔔 Notificações", callback_data="toggle_notifs")
    )
    markup.add(InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="main_menu"))
    return markup

def check_payment_keyboard(transaction_id: str, product_id: int):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 Verificar Pagamento", callback_data=f"check_{transaction_id}_{product_id}"))
    markup.add(InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="main_menu"))
    return markup

def check_deposit_keyboard(transaction_id: str, amount: float):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 Verificar Depósito", callback_data=f"checkdep_{transaction_id}_{amount}"))
    markup.add(InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="main_menu"))
    return markup

def admin_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("➕ Adicionar Estoque", callback_data="adm_add_stock"),
        InlineKeyboardButton("📦 Gerenciar Produtos", callback_data="adm_manage_products"),
        InlineKeyboardButton("🔙 Sair do Painel", callback_data="main_menu")
    )
    return markup

def back_to_main_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="main_menu"))
    return markup
