from sqlalchemy.orm import Session
from app.db_models import DBEvent

def get_conversion_funnel_data(store_id: str, db: Session):
    # Visitors Entered (ENTRY events)
    visitors_entered = db.query(DBEvent.visitor_id).filter(
        DBEvent.store_id == store_id,
        DBEvent.event_type == "ENTRY"
    ).distinct().count()

    # Fallback to unique visitors overall if 0
    if visitors_entered == 0:
        visitors_entered = db.query(DBEvent.visitor_id).filter(
            DBEvent.store_id == store_id
        ).distinct().count()

    # Visitors Visited Shelf (visited 'Shelf A' or 'Shelf B')
    visitors_visited_shelf = db.query(DBEvent.visitor_id).filter(
        DBEvent.store_id == store_id,
        (DBEvent.zone_id.like('%Shelf%') | DBEvent.zone_id.like('%shelf%'))
    ).distinct().count()

    # Visitors Billed (entered 'Billing Counter' or had PURCHASE event)
    visitors_billed = db.query(DBEvent.visitor_id).filter(
        DBEvent.store_id == store_id,
        (DBEvent.event_type == "PURCHASE") | (DBEvent.zone_id.like('%Billing%')) | (DBEvent.zone_id.like('%billing%'))
    ).distinct().count()

    # Logical validation: ensure counts follow funnel constraints for visual correctness
    if visitors_visited_shelf > visitors_entered:
        visitors_visited_shelf = visitors_entered
    if visitors_billed > visitors_visited_shelf:
        visitors_billed = visitors_visited_shelf

    conversion_rate = 0.0
    if visitors_entered > 0:
        conversion_rate = round((visitors_billed / visitors_entered) * 100.0, 2)

    return {
        "store_id": store_id,
        "visitors_entered": visitors_entered,
        "visitors_visited_shelf": visitors_visited_shelf,
        "visitors_billed": visitors_billed,
        "conversion_rate": conversion_rate
    }
