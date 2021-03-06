#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import ( Flask,
                    render_template,
                    request, 
                    Response, 
                    flash, 
                    redirect, 
                    url_for)
from sqlalchemy import func, update, desc, and_
from sqlalchemy.orm import load_only
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
import sys
from datetime import datetime

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String(120)))  
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(500), default='')

    shows = db.relationship(
      'Show', 
      backref='venue', 
      lazy='joined', 
      cascade="all, delete"
    )

class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String(120)))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(500), default='')

    shows = db.relationship(
      'Show', 
      backref='artist', 
      lazy='joined', 
      cascade="all, delete"
    )

class Show(db.Model):
    __tablename__ = 'Show'

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    start_time = db.Column(db.DateTime(), nullable=False)


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  # check value type
  if not isinstance(value, datetime):
    date = dateutil.parser.parse(value)
  else:
    date = value

  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  # TODO: replace with real venues data. --done
  #       num_upcoming_shows should be aggregated based on number of upcoming shows per venue. <------
  data=[]
  areas = ( 
    Venue.query.distinct('city', 'state')
      .options(load_only(Venue.city, Venue.state))
      .order_by(Venue.city)
      .all()
  )

  for area in areas:
    
    venues = (
      Venue.query.join(Show, and_(Venue.id==Show.venue_id, Show.start_time >= func.now()), full=True)
        .add_columns(Venue.id, Venue.name, func.count(Show.venue_id).label('num_upcoming_shows'))
        .group_by(Venue.id)
        .filter(Venue.city==area.city, Venue.state==area.state)
        .order_by(Venue.name)
        .all()
    )

    data.append({
      'city': area.city,
      'state': area.state,
      'venues': venues
    })

  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # TODO: implement search on artists with partial string search. Ensure it is case-insensitive. --done
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
  response = {}
  ilike_search = f"%{request.form['search_term']}%"
  print(ilike_search)
  venue_search = Venue.query.filter(Venue.name.ilike(ilike_search))
  print(venue_search)
  response['count']= venue_search.count()
  response['data']= venue_search.all()
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  # TODO: replace with real venue data from the venues table, using venue_id --done
  data = {}
  past_shows = []
  upcoming_shows = []
  venue = Venue.query.filter_by(id=venue_id).first()
  data.update({
    "id": venue.id,
    "name": venue.name,
    "genres": venue.genres,
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website_link,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link
  })
  events = Show.query.filter_by(venue_id=venue_id).all()
  for event in events:
    event_data={}
    event_data.update({
      "artist_id": event.artist_id,
      "artist_name": event.artist.name,
      "artist_image_link": event.artist.image_link,
      "start_time": event.start_time
    })
    if (event.start_time >= datetime.now()) :
      upcoming_shows.append(event_data)
    else:  
      past_shows.append(event_data)

  data.update({
    'upcoming_shows': upcoming_shows,
    'past_shows': past_shows,
    'past_shows_count': len(past_shows),
    'upcoming_shows_count': len(upcoming_shows),
  })
  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  # TODO: insert form data as a new Venue record in the db, instead --done
  #  Implement form submissions for creating new Venues, Artists, and Shows.
  #  There should be proper constraints, powering the /create endpoints that
  #  serve the create form templates, to avoid duplicate or nonsensical form
  #  submissions. Submitting a form should create proper new records in the database.
  # TODO: modify data to be the data object returned from db insertion
  error = False
  try:
    form = VenueForm()
    venue = Venue()
    form.populate_obj(venue)
    db.session.add(venue)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()    
  if error:
    flash('A Problem occured. Venue ' + request.form['name'] + ' was not listed!')
  else:
    flash('Venue ' + request.form['name'] + ' was successfully listed!')    
  return render_template('pages/home.html')    

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # TODO: Complete this endpoint for taking a venue_id, and using  --done
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
  error = False
  try:
    Show.query.filter_by(venue_id=venue_id).delete()
    venue = Venue.query.filter_by(id=venue_id).delete()
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close() 
  if error:
    flash('A Problem occured. Venue was not deleted!')
  else:
    flash('Venue was successfully deleted!')
  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that --done
  # clicking that button delete it from the db then redirect the user to the homepage
  return render_template('pages/home.html')

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  # TODO: replace with real data returned from querying the database --done
  return render_template('pages/artists.html', artists=Artist.query.all())

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # TODO: implement search on artists with partial string search. Ensure it is case-insensitive. --done
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
  response = {}
  ilike_search = f"%{request.form['search_term']}%"
  artist_search = Artist.query.filter(Artist.name.ilike(ilike_search))
  response['count']= artist_search.count()
  response['data']= artist_search.all()
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the artist page with the given artist_id
  # TODO: replace with real artist data from the artist table, using artist_id --done
  data = {}
  past_shows = []
  upcoming_shows = []
  artist = Artist.query.filter_by(id=artist_id).first()
  data.update({
    "id": artist.id,
    "name": artist.name,
    "genres": artist.genres, # TODO: FIX 
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website_link,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link
  })
  events = Show.query.filter_by(artist_id=artist_id).all()
  for event in events:
    event_data={}
    event_data.update({
      "venue_id": event.venue_id,
      "venue_name": event.venue.name,
      "venue_image_link": event.venue.image_link,
      "start_time": event.start_time
    })
    if (event.start_time >= datetime.now()) :
      upcoming_shows.append(event_data)
    else:  
      past_shows.append(event_data)

  data.update({
    'upcoming_shows': upcoming_shows,
    'past_shows': past_shows,
    'past_shows_count': len(past_shows),
    'upcoming_shows_count': len(upcoming_shows),
  })
  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  artist = Artist.query.get(artist_id)
  form = ArtistForm(obj=artist)
  # TODO: populate form with fields from artist with ID <artist_id> --done
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # TODO: take values from the form submitted, and update existing --done
  # artist record with ID <artist_id> using the new attributes
  error = False
  try:
    form = ArtistForm()
    artist = db.session.query(Artist).filter(Artist.id == artist_id).first()
    form.populate_obj(artist)    
    db.session.add(artist)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()    
  if error:
    flash('An error occured. Artist ' + request.form['name'] + ' was not updated!')
  else:
    flash('Artist ' + request.form['name'] + ' was successfully updated')
  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = Venue.query.get(venue_id)
  form = VenueForm(obj=venue)
  # TODO: populate form with values from venue with ID <venue_id> --done
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # TODO: take values from the form submitted, and update existing --done
  # venue record with ID <venue_id> using the new attributes
  error = False
  try:
    form = VenueForm()
    venue = db.session.query(Venue).filter(Venue.id == venue_id).first()
    form.populate_obj(venue)
    db.session.add(venue)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()    
  if error:
    flash('A Problem occured. Venue ' + request.form['name'] + ' was not updated!')
  else:
    flash('Venue ' + request.form['name'] + ' was successfully updated')

  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  # TODO: insert form data as a new Venue record in the db, instead --done
  # TODO: modify data to be the data object returned from db insertion
  error = False
  try:
    form = ArtistForm()    
    artist = Artist()
    form.populate_obj(artist)
    db.session.add(artist)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()    
  if error:
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
  else:
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  # TODO: on unsuccessful db insert, flash an error instead. --done
  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  # TODO: replace with real venues data. --done
  data=[]
  shows = Show.query.order_by(desc(Show.start_time)).all()
  for show in shows:
    data.append({
      'venue_id': show.venue_id,
      'venue_name': show.venue.name,
      "artist_id": show.artist_id,
      "artist_name": show.artist.name,
      "artist_image_link": show.artist.image_link,
      "start_time": show.start_time
    })
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  # TODO: insert form data as a new Show record in the db, instead --done
  error = False
  try:
    form = ShowForm()
    show = Show()
    form.populate_obj(show)
    db.session.add(show)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()
  if error:
    flash('An error occurred. Show could not be listed.')
  else:
    flash('Show was successfully listed!')   
  # TODO: on unsuccessful db insert, flash an error instead. --done
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
