
var requestify = require('requestify'); 
var express = require('express');
var router = express.Router();



/* GET users listing. */
router.get('/', function(req, res, next) {
     
    requestify.get('https://api.weatherbit.io/v2.0/current?city=Trento,TN&key=245ea69ec9a14549ae68a8c0371e5eb4').then(function(response) {
    // Get the response body (JSON parsed - JSON response or jQuery object in case of XML response)
    console.log(response.getBody());

    // Get the response raw body
    res.send(response.body);

});

});

module.exports = router;
