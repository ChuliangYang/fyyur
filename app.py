# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
from datetime import datetime
from string import Template
from sqlalchemy import func

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db, compare_type=True)


# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    website = db.Column(db.String(120))
    facebook_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))
    shows = db.relationship('Show', backref='venue')

class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    website = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))
    shows = db.relationship('Show', backref='artist')

    # implement any missing fields, as a database migration using Flask-Migrate

class Show(db.Model):
    __tablename__ = 'Show'

    id = db.Column(db.Integer, primary_key=True)
    venues_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
    start_time = db.Column(db.String, nullable=False)


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    cityStateList = db.session.query(Venue).distinct(Venue.city, Venue.state).all()
    newData = []
    for cityState in cityStateList:
        venus = db.session.query(Venue).filter(Venue.city == cityState.city, Venue.state == cityState.state)
        cityStateItem = {
            "city": cityState.city,
            "state": cityState.state,
            "venues": []
        }
        for venue in venus:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            venueItem = {
                "id": venue.id,
                "name": venue.name,
                "num_upcoming_shows": len(
                    db.session.query(Show).filter(Show.venues_id == venue.id, Show.start_time >= current_time).all())
            }
            cityStateItem['venues'].append(venueItem)
        newData.append(cityStateItem)

    return render_template('pages/venues.html', areas=newData)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    # seach for Hop should return "The Musical Hop".
    # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
    keyword = request.form.get('search_term', '')

    venuelist = db.session.query(Venue.id, Venue.name, func.count(Show.id).label('num_upcoming_shows')).join(Show,
                                                                                                             isouter=True).filter(
        Venue.name.ilike(Template("%${keyword}%").substitute(keyword=keyword))).group_by(Venue.id).all()

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    newData = []

    for venueItem in venuelist:
        result = db.session.query(Venue.id, func.count(Show.id).label('num_upcoming_shows')).join(Show,
                                                                                                  isouter=True).filter(
            Venue.id == venueItem.id, Show.start_time > current_time).group_by(Venue.id).first()
        num_upcoming_shows = 0
        if result is not None:
            num_upcoming_shows = result.num_upcoming_shows
        newItem = {
            "id": venueItem.id,
            "name": venueItem.name,
            "num_upcoming_shows": num_upcoming_shows
        }
        newData.append(newItem)

    response = {
        "count": len(newData),
        "data": newData
    }
    return render_template('pages/search_venues.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    chosenVenue = db.session().query(Venue).filter(Venue.id == venue_id).first()

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    pastShowList = db.session.query(Artist.id.label('artist_id'), Artist.name.label('artist_name'),
                                    Artist.image_link.label('artist_image_link'),
                                    Show.start_time.label('start_time')).join(Show).filter(Show.venues_id == venue_id,
                                                                                           Show.start_time < current_time).all()

    upcomingShowList = db.session.query(Artist.id.label('artist_id'), Artist.name.label('artist_name'),
                                        Artist.image_link.label('artist_image_link'),
                                        Show.start_time.label('start_time')).join(Show).filter(
        Show.venues_id == venue_id, Show.start_time >= current_time).all()

    data = {
        "id": chosenVenue.id,
        "name": chosenVenue.name,
        "genres": chosenVenue.genres.split(','),
        "address": chosenVenue.address,
        "city": chosenVenue.city,
        "state": chosenVenue.state,
        "phone": chosenVenue.phone,
        "website": chosenVenue.website,
        "facebook_link": chosenVenue.facebook_link,
        "seeking_talent": chosenVenue.seeking_talent,
        "seeking_description": chosenVenue.seeking_description,
        "image_link": chosenVenue.image_link,
        "past_shows": pastShowList,
        "upcoming_shows": upcomingShowList,
        "past_shows_count": len(pastShowList),
        "upcoming_shows_count": len(upcomingShowList)
    }

    return render_template('pages/show_venue.html', venue=data)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    form = request.form
    venue = Venue(name=form['name'], city=form['city'], state=form['state'], address=form['address'],
                  phone=form['phone'], genres=",".join(form.getlist('genres')), facebook_link=form['facebook_link'])

    try:
        db.session.add(venue)
        db.session.commit()
        flash('Venue ' + form['name'] + ' was successfully listed!')
    except:
        db.session.rollback()
        flash('An error occurred. Venue ' + form['name'] + ' could not be listed.')
    finally:
        db.session.close()

    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.

    # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
    # clicking that button delete it from the db then redirect the user to the homepage
    return None


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    data = Artist.query.all()
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    keyword = request.form.get('search_term', '')

    artistList = db.session.query(Artist.id, Artist.name).filter(
        Artist.name.ilike(Template("%${keyword}%").substitute(keyword=keyword))).all()

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    newData = []

    for artistItem in artistList:
        result = db.session.query(Artist.id, func.count(Show.id).label('num_upcoming_shows')).join(Show).filter(
            Artist.id == artistItem.id, Show.start_time > current_time).group_by(Artist.id).first()
        num_upcoming_shows = 0
        if result is not None:
            num_upcoming_shows = result.num_upcoming_shows
        newItem = {
            "id": artistItem.id,
            "name": artistItem.name,
            "num_upcoming_shows": num_upcoming_shows
        }
        newData.append(newItem)

    response = {
        "count": len(newData),
        "data": newData
    }
    return render_template('pages/search_artists.html', results=response,
                           search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist = db.session().query(Artist).filter(Artist.id == artist_id).first()

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    pastShowList = db.session.query(Venue.id.label("venue_id"), Venue.name.label("venue_name"),
                                    Venue.image_link.label("image_link"), Show.start_time.label('start_time')).join(
        Show).filter(Show.artist_id == artist.id, Show.start_time < current_time).all()
    upcomingShowList = db.session.query(Venue.id.label("venue_id"), Venue.name.label("venue_name"),
                                        Venue.image_link.label("image_link"), Show.start_time.label('start_time')).join(
        Show).filter(Show.artist_id == artist.id, Show.start_time >= current_time).all()

    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres.split(','),
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link,
        "facebook_link": artist.facebook_link,
        "website": artist.website,
        "past_shows": pastShowList,
        "upcoming_shows": upcomingShowList,
        "past_shows_count": len(pastShowList),
        "upcoming_shows_count": len(upcomingShowList)
    }

    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = db.session().query(Artist).filter(Artist.id == artist_id).first()
    form.state.data = artist.state
    form.genres.data = [genre for genre in artist.genres.split(',')]
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    form = request.form

    artist = Artist.query.get(artist_id)

    for field in request.form:
        if field == 'genres':
            setattr(artist, field, ",".join(form.getlist(field)))
        else:
            setattr(artist, field, form.get(field))

    try:
        db.session.add(artist)
        db.session.commit()
        flash('Artist ' + form['name'] + ' was successfully updated!')
    except:
        db.session.rollback()
        flash('An error occurred. Artist ' + form['name'] + ' could not be listed.')
    finally:
        db.session.close()

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = db.session.query(Venue).filter(Venue.id == venue_id).first()
    form.state.data = venue.state
    form.genres.data = [genre for genre in venue.genres.split(',')]
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    form = request.form

    venue = Venue.query.get(venue_id)

    for field in request.form:
        if field == 'genres':
            setattr(venue, field, ",".join(form.getlist(field)))
        else:
            setattr(venue, field, form.get(field))

    try:
        db.session.add(venue)
        db.session.commit()
        flash('Venue ' + form['name'] + ' was successfully updated!')
    except:
        db.session.rollback()
        flash('An error occurred. Venue ' + form['name'] + ' could not be listed.')
    finally:
        db.session.close()

    return render_template('pages/home.html')

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    form = request.form
    artist = Artist(name=form['name'], city=form['city'], state=form['state'],
                    phone=form['phone'], genres=",".join(form.getlist('genres')), facebook_link=form['facebook_link'])
    try:
        db.session.add(artist)
        db.session.commit()
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
    except:
        db.session.rollback()
        flash('An error occurred. Artist ' + form['name'] + ' could not be listed.')
    finally:
        db.session.close()
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    data = db.session.query(Show.venues_id.label('venue_id'), Venue.name.label('venue_name'), Show.artist_id,
                            Artist.name.label('artist_name'), Artist.image_link.label('artist_image_link'),
                            Show.start_time).join(Venue).join(Artist).all()
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = request.form
    show = Show(venues_id=int(form['venue_id']), artist_id=int(form['artist_id']), start_time=form['start_time'])

    try:
        db.session.add(show)
        db.session.commit()
        flash('Show was successfully listed!')
    except:
        db.session.rollback()
        flash('An error occurred. This show could not be listed.')
    finally:
        db.session.close()
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

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
