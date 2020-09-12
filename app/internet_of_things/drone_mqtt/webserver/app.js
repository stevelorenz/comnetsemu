// Dependencies
var createError = require('http-errors');
var express = require('express');
var path = require('path');
var cookieParser = require('cookie-parser');
var logger = require('morgan');
var bodyParser = require("body-parser");
const fs = require('fs');

// Routers
var indexRouter = require('./routes/index');
var usersRouter = require('./routes/weather');

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
app.use('/', indexRouter);                                          // Index page
app.get('/drone', function(req, res, next) {                        // Display drone positions
    res.render('drone', {
        title: 'drone',
        message: (mqttClient.drone_sensor_json)
    });
});                                 
app.get('/kml', function(req, res, next) {                                  // Download drone trajectory file in kml format              
    // Create trajectory file
    fs.writeFileSync('/tmp/trajectory.kml', mqttClient.generateKML());
    
    // Download it
    const kml_file = '/tmp/trajectory.kml';
    res.download(kml_file);
});
//app.use('/weather', usersRouter);
//app.use('/sendMqtt', mqttRouter);

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

module.exports = app;