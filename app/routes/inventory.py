import logging
from flask import Blueprint, render_template, request, redirect, url_for, session
from app.models import db, User, Item, ItemType, ItemRarity, check_and_assemble_burger, update_achievement_progress, has_achievement
from app.utils import login_required, flash_message
from app.routes.helpers import update_quest_progress

logger = logging.getLogger(__name__)

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/sell_item/<int:item_id>', methods=['POST'])
@login_required
def sell_item(item_id):
    # Get the item and verify ownership
    item = db.session.query(Item).filter(
        Item.id == item_id,
        Item.user_id == session['user_id']
    ).first_or_404()

    # Check if item is tradeable
    if not item.tradeable:
        flash_message('This item cannot be sold it must be tradeable!', 'error')
        return redirect(url_for('inventory.inventory'))

    # Check if item is an artifact (has infinite uses)
    if item.infinite_uses:
        flash_message('Artifacts cannot be sold!', 'error')
        return redirect(url_for('inventory.inventory'))

    # Get the user
    user = db.session.query(User).get(session['user_id'])

    # Add crumbs to user's balance
    crumb_value = item.crumb_value or 0
    user.add_crumbs(crumb_value)

    # Remove the item
    db.session.delete(item)
    db.session.commit()

    flash_message(f'Successfully sold {item.name} for {crumb_value} crumbs!', 'success')
    return redirect(url_for('inventory.inventory'))


@inventory_bp.route('/inventory')
@login_required
def inventory():
    # Check for Sesame Seed artifact
    user = db.session.query(User).get(session['user_id'])
    has_sesame = db.session.query(Item).filter(
        Item.user_id == session['user_id'],
        Item.name == 'Sesame Seed'
    ).first() is not None
    check_and_assemble_burger(session['user_id'])
    # Check for buffed_generation achievement
    has_achievement_boost = has_achievement(session['user_id'], 'buffed_generation')
    
    # Calculate max effects based on boosts
    if has_sesame and has_achievement_boost:
        target_max = 3
    elif has_sesame or has_achievement_boost:
        target_max = 2
    else:
        target_max = 1
        
    if user.max_active_effects != target_max:
        user.max_active_effects = target_max
        db.session.commit()

    # Get all items for the user
    items = db.session.query(Item)\
        .filter(Item.user_id == session['user_id'])\
        .all()

    # Check for chad status achievement - need Everything Burger
    has_burger = db.session.query(Item).filter(
        Item.user_id == session['user_id'],
        Item.effect_type == 'burger'
    ).first() is not None
    
    if has_burger:
        update_achievement_progress(session['user_id'], 'chad_status', 1)

    # Update achievement progress with current item count
    update_achievement_progress(session['user_id'], 'hobbyist', len(items))

    # Check for collector achievement - need one trinket of each rarity
    trinket_rarities = set()
    trinket_count = 0
    perfect_items = 0
    for item in items:
        if item.type == ItemType.TRINKET:
            trinket_rarities.add(item.rarity.value.lower())
            trinket_count += 1
        if item.quality == 100:
            perfect_items += 1
    
    # Count unique non-mythical rarities
    non_mythical_count = len([r for r in trinket_rarities if r != 'mythical'])
    update_achievement_progress(session['user_id'], 'collector', non_mythical_count)
    
    # Update hoarder achievement progress
    update_achievement_progress(session['user_id'], 'hoarder', trinket_count)

    # Update perfectionist achievement progress
    update_achievement_progress(session['user_id'], 'perfectionist', perfect_items)

    # Group items by type
    grouped_items = {
        'artifacts': [],
        'consumables': [],
        'trinkets': []
    }

    for item in items:
        # Convert item to dictionary format
        item_data = {
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'rarity': item.rarity.value,
            'icon_url': item.get_icon_url(),
            'quality': item.quality,
            'uses_remaining': item.uses_remaining,
            'effect_duration': item.effect_duration,
            'acquired_at': item.acquired_at,
            'tradeable': item.tradeable,
            'crumb_value': item.crumb_value,
            'for_sale': item.for_sale
        }

        # Add to grouped items regardless of for_sale status
        if item.type == ItemType.ARTIFACT:
            grouped_items['artifacts'].append(item_data)
        elif item.type == ItemType.CONSUMABLE:
            grouped_items['consumables'].append(item_data)
        else:  # TRINKET
            grouped_items['trinkets'].append(item_data)

    # Get listed items separately
    listed_items = [item for item in items if item.for_sale]

    formatted_listed_items = [{
        'id': item.id,
        'name': item.name,
        'description': item.description,
        'rarity': item.rarity.value,
        'icon_url': item.get_icon_url(),
        'quality': item.quality,
        'sale_price': item.sale_price,
        'uses_remaining': item.uses_remaining,
        'effect_duration': item.effect_duration,
        'acquired_at': item.acquired_at,
        'tradeable': item.tradeable,
        'for_sale': item.for_sale
    } for item in listed_items]

    listed_items_count = len(listed_items)

    # Sort items by rarity and name within each category
    rarity_order = {
        'mythical': 1,
        'legendary': 2,
        'epic': 3,
        'rare': 4,
        'common': 5
    }

    for category in grouped_items:
        grouped_items[category].sort(key=lambda x: (
            rarity_order[x['rarity'].lower()],
            x['name']
        ))

    # Get active effects using the model's method
    active_effects = Item.get_active_effects(session['user_id'])

    # Format active effects for template
    formatted_effects = [{
        'name': effect.effect_type,
        'effect_type': effect.effect_type,
        'effect_value': effect.effect_value,
        'expires_at': effect.expires_at
    } for effect in active_effects]

    # Check if user has hobbyist achievement
    tradeup_unlocked = has_achievement(session['user_id'], 'hobbyist')
    logger.info(f"Tradeup unlocked: {tradeup_unlocked}")
    
    # Get user's crumb balance
    crumb_balance = user.get_crumb_balance()
    
    # Add Trading Stick check
    has_trading_stick = db.session.query(Item).filter(
        Item.user_id == session['user_id'],
        Item.name == "Trading Stick"
    ).first() is not None

    return render_template('inventory.html',
                         inventory=grouped_items,
                         active_effects=formatted_effects,
                         tradeup_unlocked=tradeup_unlocked,
                         has_trading_stick=has_trading_stick,  # Add this line
                         crumb_balance=crumb_balance,
                         user=user,
                         listed_items=formatted_listed_items,
                         listed_items_count=listed_items_count)

@inventory_bp.route('/toggle_tradeable/<int:item_id>', methods=['POST'])
@login_required
def toggle_tradeable(item_id):
    item = db.session.query(Item).filter(
        Item.id == item_id,
        Item.user_id == session['user_id'],
        Item.type.in_([ItemType.CONSUMABLE, ItemType.TRINKET])
    ).first_or_404()

    item.tradeable = not item.tradeable
    db.session.commit()

    return redirect(url_for('inventory.inventory'))