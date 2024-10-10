from flask import Flask, request, jsonify
from flask_migrate import Migrate
from models import db, Event, Ticket
from config import Config
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)

@app.route('/')
def index():
    return "Welcome to the management tickets service"

# Create an event
@app.route('/events', methods=['POST'])
def create_event() -> dict:
    
    """Function that allows you to crete an event, the 
    body  that is expected in the request must be like this:
    {
    "name": "The doors live 3",
    "start_date": "19/10/2024",
    "end_date":   "13/10/2024",
    "total_tickets": 22
}

    Returns:
        _type_: Returns an object indicating that the Event was 
        created successfully
    """
    data:dict          = request.get_json()
    name:str           = data.get('name')
    start_date_str:str = data['start_date']
    end_date_str:str   = data['end_date']
    total_tickets:int  = data['total_tickets']
    
    # Input Validation
    if not all([name, start_date_str, end_date_str, total_tickets]):
        return jsonify({"error": "Missing requeired fieds."}), 400
    
    #Convert the string input dates to a datetime object
    try:
        start_date = datetime.strptime(start_date_str, "%d/%m/%Y")
        end_date   = datetime.strptime(end_date_str, "%d/%m/%Y")
    except Exception as e:
        return jsonify({f'error: {e}'}), 400
    
    if start_date.date() < datetime.now().date():
        return jsonify({"error": "Start date must not be in the past."}), 400
    if end_date.date() < start_date.date():
        return jsonify({"error": "End date must not be before start date."}), 400
    if not (1 <= total_tickets <= 300):
        return jsonify({"error": "The number of total tickets must be between 1 and 300."}), 400

    event = Event(
        name=name,
        start_date=start_date,
        end_date=end_date,
        total_tickets=total_tickets
    )
    
    db.session.add(event)
    db.session.commit()
    
    return jsonify({"message": "Event created successfully.", "event_id": event.id}), 200

# Update an event
@app.route('/events/<int:event_id>', methods=['PUT'])
def update_event(event_id) -> dict:
    """Function that allows you to update a registry identified in
    the DB by the event_id, you need to send a body like this: 
    {
    "name": "The doors live 2",
    "start_date": "22/10/2024",
    "end_date":   "13/12/2024",
    "total_tickets": 12
}

    Args:
        event_id (_type_): id that allows you to identify which
        event you are going to update

    Returns:
        dict: An object that tells you if the  Event was updated in
        a successfully way.
    """
    #Get the event by id to update
    event              = Event.query.get_or_404(event_id)
    #get the data from the request
    data:dict          = request.get_json()
    # set the data
    name:str           = data['name']
    start_date_str:str = data['start_date']
    end_date_str:str   = data['end_date']
    total_tickets:int  = data['total_tickets']
    
    if not all([name, start_date_str, end_date_str, total_tickets]):
        return jsonify({"error": "Missing required fields."}), 400
    
    if name:
        event.name = name
        
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%d/%m/%Y")
        except Exception as e:
            return jsonify({f"error":{e}}), 400
        if start_date.date() < datetime.now().date():
            return jsonify({"error": "The start date must not be in the past."}), 400
        event.start_date = start_date
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%d/%m/%Y")
        except Exception as e:
            return jsonify({f"error":{e}}), 400
        if end_date.date() < event.start_date.date():
            return jsonify({"error": "End date must not be before start date."}), 400
        
        event.end_date = end_date
        
    if total_tickets is not None:
        if total_tickets < event.tickets_sold:
            return jsonify({"error": "You cannot reduce total tickets below tickets sold."}), 400
        if not (1 <= total_tickets <= 300):
            return jsonify({"error": "The total of tickets must be between 1 and 300."}), 400
        event.total_tickets = total_tickets
    
    db.session.commit()
    
    return jsonify({"message": "Event updated successfully."}), 200

# Delete an event
@app.route('/events/<int:event_id>', methods=['DELETE'])
def delete_event(event_id) -> dict:
    """Function that allows you to delete an event by their id

    Args:
        event_id (_type_): This function expects the event_id so in this
        way you can identify the event to be deleted

    Returns:
        dict: an object indicating if the registry was deleted successfully
        or if you cant delete the registry
    """
    event        = Event.query.get_or_404(event_id)
    current_time = datetime.now()
    
    if event.tickets_sold > 0 and event.end_date > current_time:
        return jsonify({"error": "You can't delete an event with sold tickets or before it ends."}), 400
    
    db.session.delete(event)
    db.session.commit()
    
    return jsonify({"message": "The event was deleted successfully."}), 200

# Sell process
@app.route('/events/<int:event_id>/sell', methods=['POST'])
def sell_ticket(event_id) -> dict:
    """Function that allows you to make the process of
    selling a ticket

    Args:
        event_id (_type_):id that allows you to identify for which event 
        you are going to sell a ticket

    Returns:
        dict: An object that tells you if the Ticket was sold in
        a successful way or if there was an error
    """
    event = Event.query.get_or_404(event_id)
    
    if event.tickets_sold >= event.total_tickets:
        return jsonify({"error": "No more tickets available for this event."}), 400
    
    ticket = Ticket(event_id=event_id)
    event.tickets_sold += 1
    
    db.session.add(ticket)
    db.session.commit()
    
    return jsonify({"message": "Ticket sold in a successfully way.", "ticket_id": ticket.event_id}), 201

# Redeem process
@app.route('/tickets/<int:ticket_id>/redeem', methods=['POST'])
def redeem_ticket(ticket_id):
    
    """Function that allows you to redeem a ticket that has been sold,
you can redeem a ticket for its ID

    Returns:
        _type_: An object that says if you redeemed the ticket sucsessfuly or 
        if you can't redeem the ticket
    """
    ticket = Ticket.query.get_or_404(ticket_id)
    event = ticket.event
    current_time = datetime.now()
    
    if ticket.redeemed:
        return jsonify({"error": "Ticket has already been redeemed."}), 400
    if not (event.start_date.date() <= current_time.date() <= event.end_date.date()):
        return jsonify({"error": "Ticket can only be redeemed during the event's duration."}), 400
    
    ticket.redeemed = True
    db.session.commit()
    
    return jsonify({"message": "Ticket redeemed successfully."}), 200

# Event details 
@app.route('/events/<int:event_id>', methods=['GET']) 
def get_event_details(event_id) -> dict:
    """Function that retrieves all the details for a specific event

    Args:
        event_id (_type_): Argument that allows you to filter the event

    Returns:
        dict: An object with all the data asociated to the event
    """
    event = Event.query.get(event_id)

    if not event:
        return "Event not found", 404

    tickets_redeemed = Ticket.query.filter_by(event_id=event_id, redeemed=True).count()

    event_details = {
        "name": event.name,
        "start_date": event.start_date,
        "end_date": event.end_date,
        "total_tickets": event.total_tickets,
        "tickets_sold": event.tickets_sold,
        "tickets_redeemed": tickets_redeemed
    }

    return event_details, 200

# Get all the registries
@app.route('/events', methods=['GET'])
def get_all_events() -> dict:
    """Function that allows you to retrieve
    all the events registered in the DB

    Returns:
        dict: An object with all the registries
    """

    events = Event.query.all()

    if not events:
        return "No events found", 404

    all_events:list = []
    for event in events:
        tickets_redeemed = Ticket.query.filter_by(event_id=event.id, redeemed=True).count()

        event_data = {
            "id": event.id,
            "name": event.name,
            "start_date": event.start_date,
            "end_date": event.end_date,
            "total_tickets": event.total_tickets,
            "tickets_sold": event.tickets_sold,
            "tickets_redeemed": tickets_redeemed
        }
        all_events.append(event_data)

    return {"events": all_events}, 200

if __name__ == '__main__':
    app.run(debug=True)
