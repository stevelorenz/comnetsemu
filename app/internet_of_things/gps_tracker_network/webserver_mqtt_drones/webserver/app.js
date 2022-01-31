// Dependencies
var createError = require('http-errors');
var express = require('express');
var path = require('path');
var cookieParser = require('cookie-parser');
var logger = require('morgan');
var bodyParser = require("body-parser");
const fs = require('fs');

const maxLat = 46.096244200191684
const minLat = 46.040603518369856
const maxLon = 11.139450300806237
const minLon = 11.108262519974287

// Routers
var indexRouter = require('./routes/index');
// Mqtt handler
var mqttHandler = require('./public/javascripts/mqtt');
var mqttClient = new mqttHandler();
mqttClient.connect();

// Express app
var app = express();
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({extended: true}));
app.use(logger('dev'));
app.use(express.json());
app.use(express.urlencoded({ extended: false}));
app.use(cookieParser());
app.use(express.static(path.join(__dirname, 'public')));
app.set('views', path.join(__dirname, 'views'));                    // Views
app.set('view engine', 'pug');

// Set app routes
app.use('/', indexRouter);  // Index page

// Display drone positions                                        
app.get('/positions', function(req, res, next) {                        
    mqttClient.sendMessage("current_position", "")
    mqttClient.drone_position_json = [] // Clear old positions
    setTimeout(function(){
    	res.render('drone', {
    	    title: 'positions',
    	    message: (mqttClient.drone_position_json)
    	});	
    }, 1000) // Wait for json file generation
    
}); 

// Change drone's position
app.get('/move', function(req, res, next) {  // Pass drone ID as an URL parameter here, e.g, xx.xx.xx.xx:xxxx/move?id=drone1                  
    if (req.query.id == undefined) {
    	res.render('move', {
    	    title: 'movement',
    	    message: 'You need to specify the ID of a drone to move. Like "/move?id=drone3"'
    	});
    
    }
    mqttClient.sendMessage("command_" + req.query.id, req.query.id + "_" + getRandom(minLat, maxLat) + "_" + getRandom(minLon, maxLon) + "_")
    mqttClient.drone_position_json = [] // Clear old positions
    setTimeout(function(){
    	res.render('move', {
    	    title: 'movement',
    	    message: 'New destination has been reached by ' + req.query.id
    	});	
    }, 5000) // Wait for movement
    
}); 

// Download drone positions file in kml format                                
app.get('/genmap', function(req, res, next) {                                                
    // Create positions file
    fs.writeFileSync('/tmp/positions.kml', mqttClient.generateKML());
    
    // Download it
    const kml_file = '/tmp/positions.kml';
    res.download(kml_file);
});


app.use(function(req, res, next) {                                  // catch 404 and forward to error handler
    next(createError(404));
});
app.use(function(err, req, res, next) {                             // error handler     
    // set locals, only providing error in development
    res.locals.message = err.message;
    res.locals.error = req.app.get('env') === 'development' ? err : {};

    // render the error page
    res.status(err.status || 500);
    res.render('error');
});

function getRandom(min, max) {
  return Math.random() * (max - min) + min;
}

module.exports = app;
