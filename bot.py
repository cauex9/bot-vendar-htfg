import telebot
import logging
import config
import os
import uuid
import database as db
import keyboards as kb
import payment as pay

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode='HTML')

PHOTO_PATH = "foto/menu.jpg"

def edit_message(call, text, reply_markup):
    try:
        if call.message.content_type == 'photo':
            bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                     caption=text, reply_markup=reply_markup)
        else:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=text, reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Error editing message: {e}")

def get_welcome_text(user_id):
    user = db.get_user(user_id)
    balance = 0.0
    points = 0.0
    if user:
        balance = user[2]
        # In case the database was just initialized and points might not be in the tuple yet
        # though init_db should handle it. If points is the 5th element (index 4):
        points = user[4] if len(user) > 4 else 0.0
    
    points_value = points * 0.5
    
    text = (
        "💳 Bem vindo à central de vendas e gerenciamento de produtos do https://chat.whatsapp.com/BblYVKMvcs51x930pmTUf6.\n"
        "Explore o bot pelos botões abaixo. Qualquer dúvida é só chamar @Guiadopelo171c2b.\n\n"
        "🏛 <b>Carteira:</b>\n"
        f"┣ ID: <code>{user_id}</code>\n"
        f"┣ 💰 Saldo: R$ {balance:.2f}\n"
        f"┗ 💎 Pontos: {points:.2f} (~R${points_value:.2f})"
    )
    return text

user_checkout = {}

@bot.message_handler(commands=['start'])
def command_start(message):
    db.add_user(message.from_user.id, message.from_user.username)
    
    # Check for referral
    args = message.text.split()
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
            db.set_referral(message.from_user.id, referrer_id)
        except ValueError:
            pass
            
    welcome_text = get_welcome_text(message.from_user.id)
    
    if os.path.exists(PHOTO_PATH):
        with open(PHOTO_PATH, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=welcome_text, reply_markup=kb.main_menu_keyboard())
    else:
        bot.send_message(message.chat.id, welcome_text, reply_markup=kb.main_menu_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def callback_main_menu(call):
    text = get_welcome_text(call.from_user.id)
    edit_message(call, text, kb.main_menu_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "shop")
def callback_shop(call):
    text = "🛒 <b>Loja</b>\nEscolha uma categoria:"
    edit_message(call, text, kb.categories_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def callback_category(call):
    category_id = int(call.data.split("_")[1])
    text = "📦 <b>Produtos</b>\nSelecione o produto desejado:"
    edit_message(call, text, kb.products_keyboard(category_id))

@bot.callback_query_handler(func=lambda call: call.data.startswith("prod_"))
def callback_product(call):
    product_id = int(call.data.split("_")[1])
    product = db.get_product(product_id)
    
    if not product:
        bot.answer_callback_query(call.id, "Produto não encontrado!", show_alert=True)
        return
        
    _, _, name, description, price, stock = product
    
    text = (
        f"📦 <b>Produto:</b> {name}\n\n"
        f"📝 <b>Descrição:</b>\n{description}\n\n"
        f"💵 <b>Preço:</b> R$ {price:.2f}"
    )
    edit_message(call, text, kb.product_detail_keyboard(product_id))

@bot.callback_query_handler(func=lambda call: call.data == "profile")
def callback_profile(call):
    user = db.get_user(call.from_user.id)
    if user:
        # (user_id, username, balance, total_spent, points)
        balance = user[2]
        total_spent = user[3]
        points = user[4] if len(user) > 4 else 0.0
        text = (
            f"👤 <b>Seu Perfil</b>\n\n"
            f"🆔 <b>ID:</b> <code>{call.from_user.id}</code>\n"
            f"💰 <b>Saldo:</b> R$ {balance:.2f}\n"
            f"🛍 <b>Total Gasto:</b> R$ {total_spent:.2f}\n"
            f"💎 <b>Pontos:</b> {points:.2f}"
        )
        edit_message(call, text, kb.profile_keyboard())
    else:
        bot.answer_callback_query(call.id, "Erro ao carregar perfil.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "cc")
def callback_cc(call):
    text = (
        "💳 <b>Comprar CC</b>\n\n"
        "<i>(A funcionalidade de geração de PIX dinâmico está em desenvolvimento no módulo de pagamento)</i>\n"
        "Em breve você poderá gerar seu QR Code aqui."
    )
    edit_message(call, text, kb.back_to_main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "support")
def callback_support(call):
    text = "🆘 <b>Suporte</b>\n\nPara dúvidas ou problemas, contate o administrador: @Guiadopelo171c2b"
    edit_message(call, text, kb.back_to_main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "add_balance")
def callback_add_balance(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💰 <b>Adicionar Saldo</b>\n\nQual valor você deseja adicionar?\n\n🔹 Mínimo: <b>R$ 10,00</b>\n🔹 Máximo: <b>R$ 50,00</b>\n\nDigite apenas o número (Ex: 25):")
    bot.register_next_step_handler(msg, process_add_balance_amount)

def process_add_balance_amount(message):
    try:
        amount = float(message.text.replace(",", "."))
        if amount < 10.0 or amount > 50.0:
            bot.send_message(message.chat.id, "❌ O valor de depósito deve ser entre <b>R$ 10.00</b> e <b>R$ 50.00</b>. Tente novamente.")
            return
        
        user_id = message.from_user.id
        client_data = {
            'name': message.from_user.full_name or message.from_user.first_name,
            'email': f"user{user_id}@telegram.com", # Default email for balance top-up
            'document': "12345678909" # Placeholder document
        }
        
        identifier = f"dep_{user_id}_{str(uuid.uuid4())[:6]}"
        bot.send_message(message.chat.id, "⏳ Gerando seu Pix para depósito... Aguarde.")
        
        pix_data = pay.generate_pix(amount, client_data, identifier)
        
        if pix_data:
            text = (
                f"✅ <b>Pix de Depósito Gerado!</b>\n\n"
                f"💵 <b>Valor:</b> R$ {amount:.2f}\n\n"
                f"📱 <b>Copia e Cola:</b>\n<code>{pix_data['pix_code']}</code>\n\n"
                f"💡 <i>Seu saldo será creditado assim que o pagamento for confirmado.</i>"
            )
            # We use a different callback prefix for deposits: checkdep_
            bot.send_message(message.chat.id, text, reply_markup=kb.check_deposit_keyboard(pix_data['transaction_id'], amount))
        else:
            bot.send_message(message.chat.id, "❌ Erro ao gerar Pix. Verifique suas chaves.")
            
    except ValueError:
        bot.send_message(message.chat.id, "❌ Valor inválido. Digite apenas números.")


@bot.callback_query_handler(func=lambda call: call.data == "history")
def callback_history(call):
    history = db.get_sales_history(call.from_user.id)
    if not history:
        text = "📜 <b>Seu Histórico</b>\n\nVocê ainda não realizou nenhuma compra."
    else:
        text = "📜 <b>Seu Histórico de Compras</b>\n\n"
        for name, amount, date in history:
            text += f"📦 {name} - R$ {amount:.2f} ({date})\n"
    
    edit_message(call, text, kb.profile_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "affiliates")
def callback_affiliates(call):
    bot_info = bot.get_me()
    aff_link = f"https://t.me/{bot_info.username}?start={call.from_user.id}"
    
    text = (
        "👥 <b>Sistema de Afiliados</b>\n\n"
        "Convide seus amigos e ganhe <b>10%</b> de comissão sobre todos os depósitos que eles realizarem!\n\n"
        f"🔗 <b>Seu Link de Afiliado:</b>\n<code>{aff_link}</code>"
    )
    edit_message(call, text, kb.profile_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "toggle_notifs")
def callback_toggle_notifs(call):
    status = db.toggle_notifications(call.from_user.id)
    text = f"🔔 <b>Notificações</b>\n\nStatus atual: {'✅ Ativadas' if status == 1 else '❌ Desativadas'}"
    bot.answer_callback_query(call.id, f"Notificações {'ativadas' if status == 1 else 'desativadas'}")
    edit_message(call, text, kb.profile_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def callback_buy(call):
    product_id = int(call.data.split("_")[1])
    product = db.get_product(product_id)
    
    if not product:
        bot.answer_callback_query(call.id, "Produto não encontrado!", show_alert=True)
        return
    
    user_id = call.from_user.id
    amount = product[4]
    product_name = product[2]
    
    # Using placeholders instead of asking user
    client_data = {
        'name': call.from_user.full_name or call.from_user.first_name,
        'email': f"user{user_id}@telegram.com",
        'document': "12345678909"
    }
    
    identifier = f"buy_{user_id}_{str(uuid.uuid4())[:6]}"
    
    bot.answer_callback_query(call.id, "Gerando Pix...")
    bot.send_message(call.message.chat.id, "⏳ Gerando seu Pix... Aguarde um momento.")
    
    pix_data = pay.generate_pix(amount, client_data, identifier)
    
    if pix_data:
        text = (
            f"✅ <b>Pix Gerado com Sucesso!</b>\n\n"
            f"📦 <b>Produto:</b> {product_name}\n"
            f"💵 <b>Valor:</b> R$ {amount:.2f}\n\n"
            f"📱 <b>Copia e Cola:</b>\n<code>{pix_data['pix_code']}</code>\n\n"
            f"💡 <i>Após o pagamento, clique no botão abaixo para receber seu produto.</i>"
        )
        bot.send_message(call.message.chat.id, text, reply_markup=kb.check_payment_keyboard(pix_data['transaction_id'], product_id))
    else:
        bot.send_message(call.message.chat.id, "❌ Erro ao gerar o Pix. Verifique suas chaves API.", reply_markup=kb.main_menu_keyboard())

# --- DELETED STEPS ---
    
    if user_id in user_checkout:
        del user_checkout[user_id]

@bot.callback_query_handler(func=lambda call: call.data.startswith("check_"))
def callback_check_payment(call):
    # Format: check_transactionId_productId
    parts = call.data.split("_")
    transaction_id = parts[1]
    product_id = int(parts[2])
    
    bot.answer_callback_query(call.id, "Verificando pagamento...")
    
    status_data = pay.check_status(transaction_id)
    
    if status_data and status_data.get('status') == 'OK':
        item = db.deliver_product(call.from_user.id, product_id)
        if item:
            text = (
                "🎉 <b>Pagamento Confirmado!</b>\n\n"
                "Aqui está o seu produto:\n"
                f"<code>{item}</code>\n\n"
                "Obrigado pela compra! 💎"
            )
            bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                     caption=text, reply_markup=kb.main_menu_keyboard())
        else:
            bot.answer_callback_query(call.id, "Erro na entrega ou estoque vazio. Contate o suporte!", show_alert=True)
    else:
        current_status = status_data.get('status', 'PENDING') if status_data else 'PENDING'
        bot.answer_callback_query(call.id, f"Pagamento ainda não detectado. Status: {current_status}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("checkdep_"))
def callback_check_deposit(call):
    # Format: checkdep_transactionId_amount
    parts = call.data.split("_")
    transaction_id = parts[1]
    amount = float(parts[2])
    
    bot.answer_callback_query(call.id, "Verificando depósito...")
    
    status_data = pay.check_status(transaction_id)
    
    if status_data and status_data.get('status') == 'OK':
        db.add_balance(call.from_user.id, amount)
        text = (
            "🎉 <b>Depósito Confirmado!</b>\n\n"
            f"💰 R$ {amount:.2f} foram adicionados ao seu saldo.\n\n"
            "Aproveite as compras! 💎"
        )
        edit_message(call, text, kb.main_menu_keyboard())
    else:
        current_status = status_data.get('status', 'PENDING') if status_data else 'PENDING'
        bot.answer_callback_query(call.id, f"Depósito não detectado. Status: {current_status}", show_alert=True)

# --- ADMIN PANEL ---

@bot.message_handler(commands=['adm'])
def command_adm(message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    bot.send_message(message.chat.id, "🛠 <b>Painel Administrativo</b>\nEscolha uma opção:", reply_markup=kb.admin_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "adm_panel")
def callback_adm_panel(call):
    if call.from_user.id not in config.ADMIN_IDS: return
    text = "🛠 <b>Painel Administrativo</b>\nEscolha uma opção:"
    edit_message(call, text, kb.admin_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "adm_add_stock")
def callback_adm_add_stock(call):
    if call.from_user.id not in config.ADMIN_IDS: return
    text = "➕ <b>Adicionar Estoque</b>\nSelecione a categoria do produto:"
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup()
    for cat_id, cat_name in db.get_categories():
        markup.add(InlineKeyboardButton(cat_name, callback_data=f"admcat_{cat_id}"))
    markup.add(InlineKeyboardButton("🔙 Voltar", callback_data="adm_panel"))
    edit_message(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admcat_"))
def callback_adm_cat(call):
    if call.from_user.id not in config.ADMIN_IDS: return
    cat_id = int(call.data.split("_")[1])
    text = "📦 <b>Selecione o Produto</b> para adicionar estoque:"
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup()
    products = db.get_products_by_category(cat_id)
    for prod_id, prod_name, _ in products:
        markup.add(InlineKeyboardButton(prod_name, callback_data=f"admprod_{prod_id}"))
    markup.add(InlineKeyboardButton("🔙 Voltar", callback_data="adm_add_stock"))
    edit_message(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admprod_"))
def callback_adm_prod(call):
    if call.from_user.id not in config.ADMIN_IDS: return
    prod_id = int(call.data.split("_")[1])
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📝 Envie os itens para o estoque (um por linha):")
    bot.register_next_step_handler(msg, process_add_stock, prod_id)

def process_add_stock(message, prod_id):
    if message.from_user.id not in config.ADMIN_IDS: return
    items = [line.strip() for line in message.text.split("\n") if line.strip()]
    if not items:
        bot.send_message(message.chat.id, "❌ Nenhum item enviado. Operação cancelada.")
        return
    
    db.add_stock(prod_id, items)
    bot.send_message(message.chat.id, f"✅ {len(items)} itens adicionados ao estoque!", reply_markup=kb.admin_keyboard())

if __name__ == "__main__":
    db.init_db()
    logging.info("Database initialized.")
    logging.info("Bot is running...")
    bot.infinity_polling()
