function get_endereco(psid)
{
    var url = '/marviin/api/rest/endereco_cliente';
    if (psid)
        url += '?psid='+psid
    else
        url += '/' + $('input#path').val();
    $.getJSON( url, function( data ) {
        if(data && data.length)
        {
            $('#lista-enderecos').html('');
            data.forEach(function (item, index){
                var label = $('<label></label>').attr('class', 'endereco');
                var input = $('<input></input>')
                    .attr('type', 'radio')
                    .attr('name', 'endereco_entrega')
                    .attr('value', item.id);
                if(item.padrao == true)
                    input.prop('checked', true);
                var endereco = ' ' + item.endereco + ' ' + item.complemento + ', ' + item.bairro + ', CEP: ' + item.cep + ', ' + item.cidade + ', ' + item.estado;
                label.append(input).append($('<span></span>').append(endereco));
                $('#lista-enderecos').append(label);
            });
            $('form#form-endereco').validate({
                rules: {
                    endereco_entrega: { required: true },
                },
                submitHandler: function(form) {
                    if(psid)
                        form.action += '&psid=' + psid;
                    form.submit();
                },
                onfocusout: false,
                onkeyup: false,
                onclick: false
            });
            $('button#btn-escolher-endereco').removeClass('none');
        }
        else
            $('#lista-enderecos').html('Nenhum endereço encontrado. Utilize o botão abaixo para cadastrar seu endereço de entrega. Obrigado.');
        $('a#btn-adicionar-endereco').removeClass('none');
    })
    .fail(function(error) {
        if(error.message)
            $('#lista-enderecos').html(error.message);
        else
            $('#lista-enderecos').html('Desculpe, mas não foi possível recuperar seus endereços, por favor, refaça o login e tente novamente.');
    })
    .always(function() {
        $('div.loading-marviin').removeClass('block');
    });
}

function process_action(psid)
{
    if(!!$('div.close-window')[0])
    {
        alert('TODO: fechar janela.');
    }
    $('button#btn-escolher-endereco').on('click', function (e){
        if($(this).hasClass('nosubmit') && !!$('[type=radio]:checked')[0])
        {
            $(this).removeClass('nosubmit');
        }
        if($(this).hasClass('nosubmit'))
        {
            e.preventDefault();
            return false;
        }
        $(this).addClass('nosubmit');
    });
    $.extend(
        $.validator.messages, {
            required: 'Campo obrigatório.',
        }
    );
    get_endereco(psid);
}

function error_handler(err)
{
    $('#lista-enderecos').html('Desculpe, mas não consegui recuperar seus endereços, por favor, refaça o login e tente novamente.');
}


window.fbAsyncInit = function() {
  FB.init({
    appId      : '1147337505373379',
    cookie     : true,  // enable cookies to allow the server to access
                        // the session
    xfbml      : true,  // parse social plugins on this page
    version    : 'v2.7' // use graph api version 2.5
  });

  // Now that we've initialized the JavaScript SDK, we call
  // FB.getLoginStatus().  This function gets the state of the
  // person visiting this page and can return one of three states to
  // the callback you provide.  They can be:
  //
  // 1. Logged into your app ('connected')
  // 2. Logged into Facebook, but not your app ('not_authorized')
  // 3. Not logged into Facebook and can't tell if they are logged into
  //    your app or not.
  //
  // These three cases are handled in the callback function.

  checkLoginState();
};

// Load the SDK asynchronously
(function(d, s, id) {
    var js, fjs = d.getElementsByTagName(s)[0];
    if (d.getElementById(id)) return;
    js = d.createElement(s); js.id = id;
    js.src = "//connect.facebook.net/pt_BR/sdk.js";
    fjs.parentNode.insertBefore(js, fjs);
}(document, 'script', 'facebook-jssdk'));

function checkLoginState() {
    FB.getLoginStatus(function(response) {
      statusChangeCallback(response);
    });
}

function statusChangeCallback(response) {
    // The response object is returned with a status field that lets the
    // app know the current login status of the person.
    // Full docs on the response object can be found in the documentation
    // for FB.getLoginStatus().
    if (response.status === 'connected') {
      // Logged into your app and Facebook.
      alert('logado');
    } else if (response.status === 'not_authorized') {
      // The person is logged into Facebook, but not your app.
      alert('nao autorizado');
    } else {
      // The person is not logged into Facebook, so we're not sure if
      // they are logged into this app or not.
      alert('nao logado');
    }
}