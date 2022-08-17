#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import sys
from datetime import datetime
import babel
from flask import Flask, render_template, jsonify, request, Response, abort, flash, redirect, url_for
from flask_moment import Moment
from sqlalchemy import func, literal
import logging
from logging import Formatter, FileHandler
from flask_wtf import FlaskForm
from forms import *
from flask_migrate import Migrate
import os
import re
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.types import ARRAY
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
    genres = db.Column(MutableList.as_mutable(
        ARRAY(db.String(60))), default=[])
    phone = db.Column(db.String(120), unique=True)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120), unique=True)
    website_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(500))
    shows = db.relationship('Show', cascade="all,delete",
                            backref='venue', lazy=True)

    def past_shows(self):
        past_shows = Show.query.with_entities(
            Show.artist_id,
            Show.start_time,
            Artist.name.label('artist_name'),
            Artist.image_link.label('artist_image_link')
        ).join(
            Show.venue
        ).join(
            Show.artist
        ).filter(
            Show.start_time < datetime.now(),
            Show.venue_id == self.id
        ).all()
        return [
            {
                "artist_id": show.artist_id,
                "artist_name": show.artist_name,
                "artist_image_link": show.artist_image_link,
                "start_time": show.start_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            } for show in past_shows
        ]

    def upcoming_shows(self):
        upcoming_shows = Show.query.with_entities(
            Show.artist_id,
            Show.start_time,
            Artist.name.label('artist_name'),
            Artist.image_link.label('artist_image_link')
        ).join(
            Show.venue
        ).join(
            Show.artist
        ).filter(
            Show.start_time > datetime.now(),
            Show.venue_id == self.id
        ).all()
        return [
            {
                "artist_id": show.artist_id,
                "artist_name": show.artist_name,
                "artist_image_link": show.artist_image_link,
                "start_time": show.start_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            } for show in upcoming_shows
        ]

    def past_shows_count(self):
        return db.session.query(
            db.func.count(Show.id)
        ).filter(
            Show.start_time < datetime.now(),
            Show.venue_id == self.id
        ).scalar()

    def upcoming_shows_count(self):
        return db.session.query(
            db.func.count(Show.id)
        ).filter(
            Show.start_time > datetime.now(),
            Show.venue_id == self.id
        ).scalar()


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120), unique=True)
    genres = db.Column(MutableList.as_mutable(
        ARRAY(db.String(60))), default=[])
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120), unique=True)
    website_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(500))
    shows = db.relationship('Show', backref='artist', lazy=True)

    def past_shows(self):
        past_shows = Show.query.with_entities(
            Show.venue_id,
            Show.start_time,
            Venue.name.label('venue_name'),
            Venue.image_link.label('venue_image_link')
        ).join(
            Show.venue
        ).join(
            Show.artist
        ).filter(
            Show.start_time < datetime.now(),
            Show.artist_id == self.id
        ).all()
        return [
            {
                "venue_id": show.venue_id,
                "venue_name": show.venue_name,
                "venue_image_link": show.venue_image_link,
                "start_time": show.start_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            } for show in past_shows
        ]

    def upcoming_shows(self):
        upcoming_shows = Show.query.with_entities(
            Show.venue_id,
            Show.start_time,
            Venue.name.label('venue_name'),
            Venue.image_link.label('venue_image_link')
        ).join(
            Show.venue
        ).join(
            Show.artist
        ).filter(
            Show.start_time > datetime.now(),
            Show.artist_id == self.id
        ).all()
        return [
            {
                "venue_id": show.venue_id,
                "venue_name": show.venue_name,
                "venue_image_link": show.venue_image_link,
                "start_time": show.start_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            } for show in upcoming_shows
        ]

    def past_shows_count(self):
        return db.session.query(
            db.func.count(Show.id)
        ).filter(
            Show.start_time < datetime.now(),
            Show.artist_id == self.id
        ).scalar()

    def upcoming_shows_count(self):
        return db.session.query(
            db.func.count(Show.id)
        ).filter(
            Show.start_time > datetime.now(),
            Show.artist_id == self.id
        ).scalar()


class Show(db.Model):
    __tablename__ = 'Show'
    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey(
        'Artist.id'), nullable=False)
    start_time = db.Column(db.DateTime(), nullable=False)


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime
error = False
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
    # replace with real venues data.
    # num_upcoming_shows should be aggregated based on number of upcoming shows per venue.
    data = []
    citiesAndStateGroups = db.session.query(
        Venue.state,
        Venue.city
    ).group_by(Venue.state, Venue.city).all()
    for group in citiesAndStateGroups:
        data.append({
            "city": group.city,
            "state": group.state,
            "venues": [{
                "id": venue.id,
                "name": venue.name,
                "num_upcoming_show": venue.upcoming_shows()
            } for venue in Venue.query.filter(
                Venue.city == group.city,
                Venue.state == group.state
            ).all()]
        })
    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form.get('search_term', '')
    looking_for = '%{0}%'.format(search_term)
    data = Venue.query.filter(
        Venue.name.ilike(looking_for)
    ).all()
    response = {
        "count": len(data),
        "data": [
            {
                "id": venue.id,
                "name": venue.name,
                "num_upcoming_shows": venue.upcoming_shows(),
            } for venue in data
        ]
    }
    return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    venue = Venue.query.get_or_404(venue_id)
    data = {
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
        "image_link": venue.image_link,
        "past_shows": venue.past_shows(),
        "upcoming_shows": venue.upcoming_shows(),
        "past_shows_count": venue.past_shows_count(),
        "upcoming_shows_count": venue.upcoming_shows_count()
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
    form = VenueForm()
    # insert form data as a new Venue record in the db, instead
    # modify data to be the data object returned from db insertion
    name = form.name.data
    city = form.city.data
    state = form.state.data
    address = form.address.data
    genres = form.genres.data
    phone = form.phone.data
    image_link = form.image_link.data
    facebook_link = form.facebook_link.data
    website_link = form.website_link.data
    seeking_talent = form.seeking_talent.data
    seeking_description = form.seeking_description.data

    if not form.validate_on_submit():
        flash(form.errors)
        return redirect(url_for('create_venue_submission'))

    else:
        error_in_insert = False
        try:
            venue = Venue(
                name=name,
                city=city,
                state=state,
                address=address,
                genres=genres,
                phone=phone,
                image_link=image_link,
                facebook_link=facebook_link,
                website_link=website_link,
                seeking_talent=seeking_talent,
                seeking_description=seeking_description
            )
            db.session.add(venue)
            db.session.commit()
            # on successful db insert, flash success
            #flash('Venue ' + venue.name + ' was successfully listed!')

        except:
            db.session.rollback()
            error_in_insert = True
            print(sys.exc_info())
            # on unsuccessful db insert, flash an error instead.
            flash('An error occurred. Venue ' +
                  form.name.data + ' could not be listed.')
        finally:
            db.session.close()

        if not error_in_insert:
            flash('Venue ' + request.form['name'] +
                  ' was successfully listed!')
            return redirect(url_for('index'))
        else:
            flash('An error occurred. Venue ' + name + ' could not be listed.')
            print("Error in create_venue_submission()")
            abort(500)


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    # Complete this endpoint for taking a venue_id, and using
    # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
    venue = Venue.query.get_or_404(venue_id)
    try:
        db.session.delete(venue)
        db.session.commit()
    except:
        db.session.rollback()
        error = True
        print(sys.exc_info())
        abort(500)
    finally:
        db.session.close()
    return jsonify({"id": venue.id})

#  Artists
#  ----------------------------------------------------------------


@app.route('/artists')
def artists():
    data = Artist.query.with_entities(Artist.id, Artist.name).all()
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    # implement search on artists with partial string search. Ensure it is case-insensitive.

    search_term = request.form.get('search_term', '')
    looking_for = '%{0}%'.format(search_term)
    data = Artist.query.filter(
        Artist.name.ilike(looking_for)
    ).all()

    response = {
        "count": len(data),
        "data": [
            {
                "id": artist.id,
                "name": artist.name,
                "num_upcoming_shows": artist.upcoming_shows(),
            } for artist in data
        ]
    }
    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # shows the artist page with the given artist_id
    # replace with real artist data from the artist table, using artist_id
    artist = Artist.query.get_or_404(artist_id)
    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": artist.website_link,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link,
        "past_shows": artist.past_shows(),
        "upcoming_shows": artist.upcoming_shows(),
        "past_shows_count": artist.past_shows_count(),
        "upcoming_shows_count": artist.upcoming_shows_count(),
    }
    return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.get_or_404(artist_id)
    # populate form with fields from artist with ID <artist_id>
    form.name.data = artist.name
    form.city.data = artist.city
    form.state.data = artist.state
    form.genres.data = artist.genres
    form.phone.data = artist.phone
    form.image_link.data = artist.image_link
    form.facebook_link.data = artist.facebook_link
    form.website_link.data = artist.website_link
    form.seeking_venue.data = artist.seeking_venue
    form.seeking_description.data = artist.seeking_description
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<artist_id>', methods=['DELETE'])
def delete_artist(artist_id):
    # Complete this endpoint for taking a artist_id, and using
    # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
    artist = Artist.query.get_or_404(artist_id)
    try:
        error_in_delete = False
        db.session.delete(artist)
        db.session.commit()
    except:
        db.session.rollback()
        error_in_delete = True
        print(sys.exc_info())
        abort(500)
    finally:
        db.session.close()
    return jsonify({"id": artist.id})


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    form = ArtistForm()

    name = form.name.data
    city = form.city.data
    state = form.state.data
    genres = form.genres.data
    phone = form.phone.data
    image_link = form.image_link.data
    facebook_link = form.facebook_link.data
    website_link = form.website_link.data
    seeking_venue = form.seeking_venue.data
    seeking_description = form.seeking_description.data

    if not form.validate_on_submit():
        flash(form.errors)
        return redirect(url_for('edit_artist_submission'))

    else:
        error_in_update = False
        try:
            artist = Artist.query.get(artist_id)
            artist.name = name
            artist.city = city
            artist.state = state
            artist.genres = genres
            artist.phone = phone
            artist.seeking_venue = seeking_venue
            artist.seeking_description = seeking_description
            artist.image_link = image_link
            artist.website_link = website_link
            artist.facebook_link = facebook_link

            db.session.commit()
            # on successful db insert, flash success
            #flash('Venue ' + venue.name + ' was successfully listed!')

        except:

            error_in_update = True
            print(sys.exc_info())
            # on unsuccessful db insert, flash an error instead.
            flash('An error occurred. Artist ' +
                  form.name.data + ' could not be listed.')
            db.session.rollback()
        finally:
            db.session.close()

        if not error_in_update:
            flash('Aritst ' + request.form['name'] +
                  ' was successfully updated!')
            return redirect(url_for('index'))
        else:
            flash('An error occurred. Artist ' +
                  name + ' could not be listed.')
            print("Error in edit_artist_submission()")
            abort(500)


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.get_or_404(venue_id)
    # populate form with values from venue with ID <venue_id>
    form.name.data = venue.name
    form.city.data = venue.city
    form.state.data = venue.state
    form.address.data = venue.address
    form.genres.data = venue.genres
    form.phone.data = venue.phone
    form.image_link.data = venue.image_link
    form.facebook_link.data = venue.facebook_link
    form.website_link.data = venue.website_link
    form.seeking_talent.data = venue.seeking_talent
    form.seeking_description.data = venue.seeking_description
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    #venue = Venue.query.get_or_404(venue_id)
    form = VenueForm()

    name = form.name.data
    city = form.city.data
    state = form.state.data
    address = form.address.data
    genres = form.genres.data
    phone = form.phone.data
    image_link = form.image_link.data
    facebook_link = form.facebook_link.data
    website_link = form.website_link.data
    seeking_talent = form.seeking_talent.data
    seeking_description = form.seeking_description.data

    if not form.validate_on_submit():
        flash(form.errors)
        return redirect(url_for('edit_venue_submission'))

    else:
        error_in_update = False
        try:
            venue = Venue.query.get(venue_id)
            venue.name = name
            venue.city = city
            venue.state = state
            venue.address = address
            venue.genres = genres
            venue.phone = phone
            venue.seeking_talent = seeking_talent
            venue.seeking_description = seeking_description
            venue.image_link = image_link
            venue.website_link = website_link
            venue.facebook_link = facebook_link

            db.session.commit()
            # on successful db insert, flash success
            #flash('Venue ' + venue.name + ' was successfully listed!')

        except:

            error_in_update = True
            print(sys.exc_info())
            # on unsuccessful db insert, flash an error instead.
            flash('An error occurred. Venue ' +
                  form.name.data + ' could not be listed.')
            db.session.rollback()
        finally:
            db.session.close()

        if not error_in_update:
            flash('Venue ' + request.form['name'] +
                  ' was successfully updated!')
            return redirect(url_for('index'))
        else:
            flash('An error occurred. Venue ' + name + ' could not be listed.')
            print("Error in create_venue_submission()")
            abort(500)


#  Create Artist
#  ----------------------------------------------------------------


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():

    form = ArtistForm()
    # insert form data as a new Venue record in the db, instead
    # modify data to be the data object returned from db insertion
    name = form.name.data
    city = form.city.data
    state = form.state.data
    genres = form.genres.data
    phone = form.phone.data
    image_link = form.image_link.data
    facebook_link = form.facebook_link.data
    website_link = form.website_link.data
    seeking_venue = form.seeking_venue.data
    seeking_description = form.seeking_description.data

    if not form.validate_on_submit():
        flash(form.errors)
        return redirect(url_for('create_artist_submission'))

    else:
        error_in_insert = False
        try:
            artist = Artist(
                name=name,
                city=city,
                state=state,
                genres=genres,
                phone=phone,
                image_link=image_link,
                facebook_link=facebook_link,
                website_link=website_link,
                seeking_venue=seeking_venue,
                seeking_description=seeking_description
            )
            db.session.add(artist)
            db.session.commit()
            # on successful db insert, flash success
            #flash('Venue ' + venue.name + ' was successfully listed!')

        except:
            error_in_insert = True
            print(sys.exc_info())
            # on unsuccessful db insert, flash an error instead.
            flash('An error occurred. Artist ' +
                  form.name.data + ' could not be listed.')
            db.session.rollback()
        finally:
            db.session.close()

        if not error_in_insert:
            flash('Artist ' + request.form['name'] +
                  ' was successfully listed!')
            return redirect(url_for('index'))
        else:
            flash('An error occurred. Artist ' +
                  name + ' could not be listed.')
            print("Error in create_artist_submission()")
            abort(500)


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # displays list of shows at /shows
    # replace with real venues data.
    shows = db.session.query(Show).with_entities(
        Show.venue_id,
        Show.artist_id,
        Show.start_time,
        Venue.name.label('venue_name'),
        Artist.name.label('artist_name'),
        Artist.image_link.label('artist_image_link'),
    ).join(Show.venue).join(Show.artist).all()

    data = [
        {
            "venue_id": show.venue_id,
            "venue_name": show.venue_name,
            "artist_id": show.artist_id,
            "artist_name": show.artist_name,
            "artist_image_link": show.artist_image_link,
            "start_time": show.start_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        } for show in shows
    ]

    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = ShowForm()
    venue = Venue.query.get(form.venue_id.data)
    artist = Artist.query.get(form.artist_id.data)
    if venue == None or artist == None:
        abort(500)

    if form.validate_on_submit():
        try:
            show = Show(
                venue=venue,
                artist=artist,
                start_time=form.start_time.data
            )
            db.session.add(venue)
            db.session.commit()
            # on successful db insert, flash success
            flash('Show was successfully listed!')
        except:
            db.session.rollback()
            error = True
            print(sys.exc_info())
            # on unsuccessful db insert, flash an error instead.
            flash('An error occurred. Show could not be listed.')
        finally:
            db.session.close()
    else:
        flash('Your input is not valide. fill required fields with good type')
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
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
# if __name__ == '__main__':
#     app.run()

# Or specify port manually:

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port)
