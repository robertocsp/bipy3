function get_lojas()
{
    var url = '/marviin/api/rest/loja/'+$('input#psidappid').val();

    $( "#campoEstabelecimento" ).autocomplete({
        width: 300,
        max: 10,
        delay: 100,
        minLength: 3,
        autoFocus: true,
        cacheLength: 1,
        scroll: true,
        highlight: false,
        source: url,
        focus: function( event, ui ) {
            $('#campoEstabelecimento').val(ui.item.label);
            return false;
        },
        select: function( event, ui ) {
            $('#campoEstabelecimento').val(ui.item.label);
            $('#loja').val(ui.item.value);
            return false;
        }
    })
    .autocomplete( 'instance' )._renderItem = function( ul, item ) {
      return $( '<li>' )
        .append( '<div>' + item.label + '</div>' )
        .appendTo( ul );
    };
}

function process_action(psid)
{
    $('button#btn-escolher-loja').on('click', function (e)
    {
        e.preventDefault();
        if($(this).hasClass('nosubmit'))
        {
            return false;
        }
        $(this).addClass('nosubmit');

        var url = '/marviin/api/rest/loja/'+$('input#psidappid').val();

        $.post(url, $('#lojasform').serialize(), function(data) {
            if(psid)
            {
                MessengerExtensions.requestCloseBrowser(function success() {
                    //nada a fazer
                }, function error(err) {
                    //TODO informar o usuário que ele pode fechar a WEBVIEW.
                });
            }
            else
            {
                window.location.href='https://www.messenger.com/closeWindow/?image_url=-&display_text=-';
            }
        })
        .fail(function(error) {
            alert(error)
//            if(error.message)
//                $('#lista-enderecos').html(error.message);
//            else
//                $('#lista-enderecos').html('Desculpe, tivemos um erro inesperado, por favor, tente novamente.')
        })
        .always(function() {
//            $('div.loading-marviin').removeClass('block');
        });
        return;
    });
    get_lojas();
}

function error_handler(err)
{
//    $('#lista-enderecos').html('Desculpe, mas não consegui recuperar seus endereços, por favor, refaça o login e tente novamente.');
}