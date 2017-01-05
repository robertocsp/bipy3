$(function() {
    (function(d, s, id){
      var js, fjs = d.getElementsByTagName(s)[0];
      if (d.getElementById(id)) {return;}
      js = d.createElement(s); js.id = id;
      js.src = "//connect.facebook.com/en_US/messenger.Extensions.js";
      fjs.parentNode.insertBefore(js, fjs);
    }(document, 'script', 'Messenger'));

    window.extAsyncInit = function() {
        var isSupported = MessengerExtensions.isInExtension();
        if(isSupported)
        {
            MessengerExtensions.getUserID(function success(uids) {
                process_action(uids.psid);
            }, function error(err) {
                //TODO post error to log
                error_handler(err);
            });
        }
        else
        {
            process_action();
        }
    };
});

//    (function(d, s, id) {
//        var js, fjs = d.getElementsByTagName(s)[0];
//        if (d.getElementById(id)) return;
//        js = d.createElement(s); js.id = id;
//        js.src = "//connect.facebook.net/pt_BR/sdk.js";
//        fjs.parentNode.insertBefore(js, fjs);
//    }(document, 'script', 'facebook-jssdk'));
//
//    window.fbAsyncInit = function() {
//      FB.init({
//        appId      : 'APP_ID',
//        cookie     : true,  // enable cookies to allow the server to access
//                            // the session
//        xfbml      : true,  // parse social plugins on this page
//        version    : 'v2.7' // use graph api version 2.5
//      });
//
//      checkLoginState();
//    };
//
//    function checkLoginState() {
//        FB.getLoginStatus(function(response) {
//          statusChangeCallback(response);
//        });
//    }
//
//    function statusChangeCallback(response) {
//        if (response.status === 'connected') {
//          alert('logado');
//        } else if (response.status === 'not_authorized') {
//          alert('nao autorizado');
//        } else {
//          alert('nao logado');
//        }
//    }