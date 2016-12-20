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