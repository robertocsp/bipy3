function generateUUID() {
    var d = new Date().getTime();
    if(window.performance && typeof window.performance.now === "function"){
        d += performance.now(); //use high-precision timer if available
    }
    var uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = (d + Math.random()*16)%16 | 0;
        d = Math.floor(d/16);
        return (c=='x' ? r : (r&0x3|0x8)).toString(16);
    });
    return uuid;
}

$(function() {
    var code = $.url().param('code');
    var state = $.url().param('state');
    if (code && state)
    {
        if(sessionStorage.stateLogin && sessionStorage.stateLogin === state)
        {
            $.post('https://sistema.marviin.com.br/marviin/api/rest/acesso_bot_v2',
                 {code: code, client_id: state.split('|')[1]},
                 function(data) {

            })
            .fail(function(data) {
                console.log(data);
                var error_handled = false;
                var error_json = get_error_json(data);
                if(error_json){
                    if (error_json.type === 'perm'){
                        carregaInfosUsuario(state.split('|')[1], 'rerequest', error_json.object.join(','));
                        error_handled = true;
                    } else if (error_json.type === 'msg'){
                        alert_error(data, error_json);
                        error_handled = true;
                    }
                }
            })
            .always(function() {
            });
        }
    }

});

function carregaInfosUsuario(client_id, auth_type, scope)
{
    var uid = generateUUID();
    sessionStorage.stateLogin = uid+'|'+client_id;
    if (!auth_type)
        auth_type = 'reauthenticate';
    if (!scope)
        scope = 'manage_pages,pages_messaging';
    var redirect_url='https://www.facebook.com/v2.8/dialog/oauth?client_id='+client_id+
        '&redirect_uri=https://acesso.marviin.com.br/'+
        '&state='+sessionStorage.stateLogin+'&scope='+scope+
        '&auth_type='+auth_type;
    window.location.href=redirect_url;
}