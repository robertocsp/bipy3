function get_endereco(psid)
{
    $.getJSON( 'https://sistema.marviin.com.br/marviin/api/rest/endereco_cliente?psid='+psid, function( data ) {
        $('#lista-enderecos').html('<label><strong>Endereço</strong></label><br />');
        data.forEach(function (item, index){
            var input = $('<input></input>')
                .attr('type', 'radio')
                .attr('name', 'endereco_entrega')
                .attr('value', item.id);
            if(item.padrao == true)
                input.prop('checked', true);
            var endereco = ' ' + item.endereco + ' ' + item.complemento + ', ' + item.bairro + ', CEP: ' + item.cep + ', ' + item.cidade + ', ' + item.estado;
            if(index > 0)
                $('#lista-enderecos').append($('<br></br>'));
            $('#lista-enderecos').append(input).append(endereco);
        });
    })
    .fail(function(error) {
        if(error.message)
            $('#lista-enderecos').html(error.message);
        else
            $('#lista-enderecos').html('Desculpe, mas não foi possível recuperar seus endereços, por favor, refaça o login e tente novamente novamente.');
    })
    .always(function() {
    });
}

function process_action(psid)
{
    get_endereco(psid);
}

function error_handler(err)
{
    $('#lista-enderecos').html('Desculpe, mas não consegui recuperar seus endereços, por favor, refaça o login e tente novamente novamente.');
}