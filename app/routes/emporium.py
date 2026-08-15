import random
import logging
from datetime import datetime
from sqlalchemy import func
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from app.models import db, User, Item, ItemType, ItemRarity, ITEMS, ActiveEffect, SHOP_ITEMS, calculate_shop_price, get_item_for_user, check_and_assemble_burger, update_achievement_progress, has_achievement, Page
from app.utils import login_required, flash_message
from app.routes.helpers import update_quest_progress

logger = logging.getLogger(__name__)

emporium_bp = Blueprint('emporium', __name__)

@emporium_bp.route('/emporium')
@login_required
def emporium():
    user = db.session.query(User).get(session['user_id'])
    
    # Get owned artifacts for disabling buttons
    owned_artifacts = db.session.query(Item.name).filter(
        Item.user_id == user.id,
        Item.type == ItemType.ARTIFACT
    ).all()
    user_owned_artifacts = {name[0]: True for name in owned_artifacts}
    
    # Get active shop discount
    discount = db.session.query(ActiveEffect).filter(
        ActiveEffect.user_id == user.id,
        ActiveEffect.effect_type == 'shop_discount',
        ActiveEffect.expires_at > datetime.utcnow()
    ).first()
    
    # Get all items listed for sale
    user_items_for_sale = db.session.query(Item).join(User).filter(
        Item.for_sale == True
    ).all()
    
    # Format items for sale for the template
    formatted_items_for_sale = [{
        'id': item.id,
        'name': item.name,
        'description': item.description,
        'rarity': item.rarity,
        'type': item.type,
        'sale_price': item.sale_price,
        'icon_url': item.get_icon_url(),
        'quality': item.quality,
        'uses_remaining': item.uses_remaining,
        'effect_duration': item.effect_duration,
        'user': {
            'username': item.user.username
        },
        'is_own_item': item.user_id == session['user_id']
    } for item in user_items_for_sale]
    
    def price_calculator(item_data):
        return calculate_shop_price(item_data, discount)
    
    return render_template('emporium.html',
                         shop_items=SHOP_ITEMS,
                         user_owned_artifacts=user_owned_artifacts,
                         calculate_shop_price=price_calculator,  # Changed this line
                         crumb_balance=user.get_crumb_balance(),
                         shop_discount=discount,
                         ItemType=ItemType,
                         user_items_for_sale=formatted_items_for_sale,
                         user=user)


@emporium_bp.route('/buy_user_item/<int:item_id>', methods=['POST'])
@login_required
def buy_user_item(item_id):
    # Get the item and verify it exists and is for sale
    item = db.session.query(Item).filter(
        Item.id == item_id,
        Item.for_sale == True
    ).first()
    
    if not item:
        flash_message('Item not found or no longer for sale', 'error')
        return redirect(url_for('emporium.emporium'))
        
    # Prevent buying your own items
    if item.user_id == session['user_id']:
        flash_message('You cannot buy your own items!', 'error')
        return redirect(url_for('emporium.emporium'))
    
    # Get buyer
    buyer = db.session.query(User).get(session['user_id'])
    
    # Check if item has a valid sale price
    if not item.sale_price or item.sale_price <= 0:
        flash_message('This item has an invalid sale price', 'error')
        return redirect(url_for('emporium.emporium'))
    
    # Check if buyer has enough crumbs
    if buyer.current_crumbs < item.sale_price:
        flash_message('Not enough crumbs!', 'error')
        return redirect(url_for('emporium.emporium'))
    
    # Get seller
    seller = db.session.query(User).get(item.user_id)
    
    # Process the transaction
    buyer.remove_crumbs(item.sale_price)
    seller.add_crumbs(item.sale_price)
    
    # Transfer item to buyer
    item.user_id = buyer.id
    item.for_sale = False
    item.sale_price = None
    
    db.session.commit()
    
    flash_message(f'Successfully purchased {item.name}!', 'success')
    return redirect(url_for('emporium.emporium'))

@emporium_bp.route('/check_cursor_effect')
@login_required
def check_cursor_effect():
    if 'user_id' not in session:
        return jsonify({'has_dragon_cursor': False})
        
    active_effects = Item.get_active_effects(session['user_id'])
    has_dragon_cursor = any(
        effect.effect_type == 'cursor' and 
        effect.effect_value == 'dragon_scimitar' 
        for effect in active_effects
    )
    
    return jsonify({'has_dragon_cursor': has_dragon_cursor})

@emporium_bp.route('/tradeup/<rarity>', methods=['POST'])
@login_required
def tradeup(rarity):
    # Add check for Trading Stick at the start
    has_trading_stick = db.session.query(Item).filter(
        Item.user_id == session['user_id'],
        Item.name == "Trading Stick"
    ).first() is not None

    # Determine required items based on Trading Stick
    required_items = 2 if (has_trading_stick and rarity != 'legendary') else 3

    # Check for hobbyist achievement before allowing tradeup
    if not has_achievement(session['user_id'], 'hobbyist'):
        flash_message('You need the Hobbyist achievement to use trade-ups!', 'error')
        return redirect(url_for('inventory.inventory'))

    valid_rarities = ['common', 'rare', 'epic', 'legendary']
    if rarity not in valid_rarities:
        flash_message('Invalid rarity for tradeup', 'error')
        return redirect(url_for('inventory.inventory'))

    # Get tradeable items of specified rarity owned by user that are not for sale
    items = db.session.query(Item).filter(
        Item.user_id == session['user_id'],
        Item.rarity == ItemRarity(rarity),
        Item.tradeable == True,
        Item.for_sale == False
    ).limit(required_items).all()

    if len(items) < required_items:
        flash_message(f'You need {required_items} tradeable {rarity} items that are not for sale for a tradeup', 'error')
        return redirect(url_for('inventory.inventory'))

    # Delete the traded items
    for item in items:
        db.session.delete(item)

    # Check for Gambler's Odds artifact
    has_gamblers_odds = db.session.query(Item).filter(
        Item.user_id == session['user_id'],
        Item.name == "Gambler's Odds"
    ).first() is not None

    # Roll for result based on rarity
    roll = random.random() * 100

    if rarity == 'common':
        if has_gamblers_odds:
            if roll < 60:  # 60% rare (up from 40%)
                new_rarity = ItemRarity.RARE
            elif roll < 85:  # 25% epic (down from 35%)
                new_rarity = ItemRarity.EPIC
            elif roll < 95:  # 10% legendary (down from 15%)
                new_rarity = ItemRarity.LEGENDARY
            else:  # 5% nothing (down from 10%)
                flash_message('Tradeup failed!', 'error')
                db.session.commit()
                return redirect(url_for('inventory.inventory'))
        else:
            if roll < 40:  # 40% rare
                new_rarity = ItemRarity.RARE
            elif roll < 75:  # 35% epic
                new_rarity = ItemRarity.EPIC
            elif roll < 90:  # 15% legendary
                new_rarity = ItemRarity.LEGENDARY
            else:  # 10% nothing
                flash_message('Tradeup failed!', 'error')
                db.session.commit()
                return redirect(url_for('inventory.inventory'))

    elif rarity == 'rare':
        if has_gamblers_odds:
            if roll < 75:  # 75% epic (up from 60%)
                new_rarity = ItemRarity.EPIC
            elif roll < 95:  # 20% legendary (down from 30%)
                new_rarity = ItemRarity.LEGENDARY
            else:  # 5% nothing (down from 10%)
                flash_message('Tradeup failed!', 'error')
                db.session.commit()
                return redirect(url_for('inventory.inventory'))
        else:
            if roll < 60:  # 60% epic
                new_rarity = ItemRarity.EPIC
            elif roll < 90:  # 30% legendary
                new_rarity = ItemRarity.LEGENDARY
            else:  # 10% nothing
                flash_message('Tradeup failed!', 'error')
                db.session.commit()
                return redirect(url_for('inventory.inventory'))

    elif rarity == 'epic':
        if has_gamblers_odds:
            if roll < 85:  # 85% 1 legendary (up from 80%)
                new_items = 1
                new_rarity = ItemRarity.LEGENDARY
            elif roll < 95:  # 10% 2 legendary (same)
                new_items = 2
                new_rarity = ItemRarity.LEGENDARY
            else:  # 5% nothing (down from 10%)
                flash_message('Tradeup failed!', 'error')
                db.session.commit()
                return redirect(url_for('inventory.inventory'))
        else:
            if roll < 80:  # 80% 1 legendary
                new_items = 1
                new_rarity = ItemRarity.LEGENDARY
            elif roll < 90:  # 10% 2 legendary
                new_items = 2
                new_rarity = ItemRarity.LEGENDARY
            else:  # 10% nothing
                flash_message('Tradeup failed!', 'error')
                db.session.commit()
                return redirect(url_for('inventory.inventory'))

    else:  # legendary
        if has_gamblers_odds:
            if roll < 65:  # 75% mythical fragment (up from 50%)
                # Create random fragment
                available_fragments = ['bun', 'patty', 'ketchup', 'pickle', 'cheese']

                # Always check existing fragments to prevent duplicates
                existing_fragments = db.session.query(Item.effect_value).filter(
                    Item.user_id == session['user_id'],
                    Item.effect_type == 'fragment'
                ).all()
                existing_fragments = [f[0] for f in existing_fragments]
                available_fragments = [f for f in available_fragments if f not in existing_fragments]

                if not available_fragments:
                    flash_message('No new fragments available! Complete your set to start a new one.', 'error')
                    db.session.commit()
                    return redirect(url_for('inventory.inventory'))

                fragment_type = random.choice(available_fragments)
                fragment_key = f'{fragment_type}_fragment'

                fragment = Item(
                    name=ITEMS[fragment_key]['name'],
                    description=ITEMS[fragment_key]['description'],
                    type=ItemType.ARTIFACT,
                    rarity=ItemRarity.MYTHICAL,
                    effect_type='fragment',
                    effect_value=fragment_type,
                    quality=100,
                    user_id=session['user_id'],
                    tradeable=False,
                    icon_url=f"/static/icons/artifacts/{fragment_type}_fragment.png"
                )
                db.session.add(fragment)
                db.session.commit()

                # Check if we can assemble a burger
                check_and_assemble_burger(session['user_id'])

                flash_message(f'Successfully created a {fragment.name}!', 'success')
                return redirect(url_for('inventory.inventory'))
            else:  # 25% nothing (down from 50%)
                flash_message('Tradeup failed!', 'error')
                db.session.commit()
                return redirect(url_for('inventory.inventory'))
        else:
            if roll < 50:  # 50% mythical fragment
                # Create random fragment
                available_fragments = ['bun', 'patty', 'ketchup', 'pickle', 'cheese']

                # Always check existing fragments to prevent duplicates
                existing_fragments = db.session.query(Item.effect_value).filter(
                    Item.user_id == session['user_id'],
                    Item.effect_type == 'fragment'
                ).all()
                existing_fragments = [f[0] for f in existing_fragments]
                available_fragments = [f for f in available_fragments if f not in existing_fragments]

                if not available_fragments:
                    flash_message('No new fragments available! Complete your set to start a new one.', 'error')
                    db.session.commit()
                    return redirect(url_for('inventory.inventory'))

                fragment_type = random.choice(available_fragments)
                fragment_key = f'{fragment_type}_fragment'

                fragment = Item(
                    name=ITEMS[fragment_key]['name'],
                    description=ITEMS[fragment_key]['description'],
                    type=ItemType.ARTIFACT,
                    rarity=ItemRarity.MYTHICAL,
                    effect_type='fragment',
                    effect_value=fragment_type,
                    quality=100,
                    user_id=session['user_id'],
                    tradeable=False,
                    icon_url=f"/static/icons/artifacts/{fragment_type}_fragment.png"
                )
                db.session.add(fragment)
                db.session.commit()

                # Check if we can assemble a burger
                check_and_assemble_burger(session['user_id'])

                flash_message(f'Successfully created a {fragment.name}!', 'success')
                return redirect(url_for('inventory.inventory'))
            else:  # 50% nothing
                flash_message('Tradeup failed!', 'error')
                db.session.commit()
                return redirect(url_for('inventory.inventory'))

    # Generate new item(s)
    # Get a random prompt from existing pages
    random_page = db.session.query(Page.prompt).order_by(func.random()).first()
    prompt = random_page.prompt if random_page else "Generate a mysterious magical item"

    # Generate new item(s)
    new_items_list = []  # Keep track of generated items
    for _ in range(new_items if 'new_items' in locals() else 1):
        # Create a new item with the desired rarity directly
        new_item = get_item_for_user(session['user_id'], prompt)
        if new_item.type != ItemType.ARTIFACT:  # Only override rarity for non-artifacts
            new_item.rarity = new_rarity
        db.session.add(new_item)
        new_items_list.append(new_item)  # Add to our list

    db.session.commit()

    # Flash success message about the new items
    if len(new_items_list) == 1:
        flash_message(f'Successfully traded up to {new_items_list[0].name}!', 'success')
    else:
        flash_message(f'Successfully traded up to {len(new_items_list)} {new_rarity.value} items!', 'success')

    # Move XP and progress updates before the return
    # Add XP for successful tradeup based on rarity
    user = db.session.query(User).get(session['user_id'])
    rarity_xp = {
        'common': 50,
        'rare': 100,
        'epic': 200,
        'legendary': 400
    }
    user.add_xp(rarity_xp.get(rarity, 50))
    
    # Update quest progress
    update_quest_progress(session['user_id'], 'trade_ups')
    
    # Check quality of new items
    for item in new_items_list:
        if item.quality > 75:
            update_quest_progress(session['user_id'], 'quality_items')

    db.session.commit()

    return redirect(url_for('inventory.inventory'))


@emporium_bp.route('/buy_item/<item_key>', methods=['POST'])
@login_required
def buy_item(item_key):
    if item_key not in SHOP_ITEMS:
        flash_message('Invalid item', 'error')
        return redirect(url_for('emporium.emporium'))
        
    item_data = SHOP_ITEMS[item_key]
    user = db.session.query(User).get(session['user_id'])
    
    # Check if user already owns artifact
    if item_data['type'] == ItemType.ARTIFACT:
        existing = db.session.query(Item).filter(
            Item.user_id == user.id,
            Item.name == item_data['name']
        ).first()
        if existing:
            flash_message('You already own this artifact!', 'error')
            return redirect(url_for('emporium.emporium'))
    
    # Get active shop discount
    discount = db.session.query(ActiveEffect).filter(
        ActiveEffect.user_id == user.id,
        ActiveEffect.effect_type == 'shop_discount',
        ActiveEffect.expires_at > datetime.utcnow()
    ).first()
    
    # Calculate price with potential discount
    price_info = calculate_shop_price(item_data, discount)
    final_price = price_info['discounted'] if price_info['discounted'] is not None else price_info['original']
    
    if user.current_crumbs < final_price:
        flash_message('Not enough crumbs!', 'error')
        return redirect(url_for('emporium.emporium'))
    
    # Create item
    new_item = Item(
        name=item_data['name'],
        description=item_data['description'],
        type=item_data['type'],
        rarity=item_data['rarity'],
        effect_type=item_data.get('effect_type'),
        effect_value=item_data.get('effect_value'),
        effect_duration=item_data.get('effect_duration'),
        uses_remaining=item_data.get('uses_remaining'),
        quality=100,
        user_id=user.id,
        tradeable=item_data['type'] != ItemType.ARTIFACT,
        icon_url=f"/static/icons/{'artifacts' if item_data['type'] == ItemType.ARTIFACT else 'consumables'}/{item_data['name'].lower().replace(' ', '_')}.png"
    )
    
    user.remove_crumbs(final_price)
    db.session.add(new_item)
    db.session.commit()
    
    flash_message(f'Successfully purchased {item_data["name"]}!', 'success')
    return redirect(url_for('emporium.emporium'))

@emporium_bp.route('/list_for_sale/<int:item_id>', methods=['POST'])
@login_required
def list_for_sale(item_id):
    price = request.form.get('price')
    logger.info(f"Attempting to list item {item_id} for price {price}")
    
    if not price or not price.isdigit():
        logger.info("Invalid price format")
        flash_message('Invalid price', 'error')
        return redirect(url_for('inventory.inventory'))
        
    price = int(price)
    if price <= 0:
        logger.info("Price must be greater than 0")
        flash_message('Price must be greater than 0', 'error')
        return redirect(url_for('inventory.inventory'))
        
    # Get all items for the user
    items = db.session.query(Item)\
        .filter(Item.user_id == session['user_id'])\
        .all()
    # Count items that are for sale
    listed_items_count = len([item for item in items if item.for_sale])
    
    logger.info(f"Current listed items count: {listed_items_count}")
    
    if listed_items_count >= 5:
        logger.info("Too many items listed")
        flash_message('You can only list up to 5 items for sale at a time', 'error')
        return redirect(url_for('inventory.inventory'))
        
    item = db.session.query(Item).filter(
        Item.id == item_id,
        Item.user_id == session['user_id']
    ).first()
    
    if not item:
        logger.info("Item not found")
        flash_message('Item not found', 'error')
        return redirect(url_for('inventory.inventory'))
        
    if not item.tradeable or item.type == ItemType.ARTIFACT:
        logger.info("Item cannot be traded")
        flash_message('This item cannot be traded', 'error')
        return redirect(url_for('inventory.inventory'))
        
    if item.for_sale:
        logger.info("Item is already listed for sale")
        flash_message('This item is already listed for sale', 'error')
        return redirect(url_for('inventory.inventory'))
        
    logger.info(f"Setting item {item_id} for sale at price {price}")
    item.for_sale = True
    item.sale_price = price
    db.session.commit()
    logger.info(f"Item listed successfully: {item.for_sale}, {item.sale_price}")
    update_quest_progress(session['user_id'], 'list_items')

    flash_message('Item listed successfully!', 'success')
    return redirect(url_for('inventory.inventory'))


@emporium_bp.route('/cancel_sale/<int:item_id>', methods=['POST'])
@login_required
def cancel_sale(item_id):
    item = db.session.query(Item).filter(
        Item.id == item_id,
        Item.user_id == session['user_id']
    ).first()
    
    if not item:
        flash_message('Item not found', 'error')
        return redirect(url_for('inventory.inventory'))
        
    item.for_sale = False
    item.sale_price = 0
    db.session.commit()
    
    flash_message(f'Cancelled sale of {item.name}', 'success')
    return redirect(url_for('inventory.inventory'))