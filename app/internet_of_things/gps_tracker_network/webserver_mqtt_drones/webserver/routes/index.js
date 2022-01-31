var mqtt_module = require('../public/javascripts/mqtt');
var express = require('express');
var router = express.Router();
var requestify = require('requestify');

/* GET home page. */
router.get('/', function (req, res) {
  res.render('index', { title: 'index', message: 'Hello index' })
})

module.exports = router;