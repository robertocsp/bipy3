function get_endereco(psid)
{
    $('div.loading-marviin').show();
    $.getJSON( '/marviin/api/rest/endereco_cliente?psid='+psid, function( data ) {
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
                label.append(input).append(endereco);
                $('#lista-enderecos').append(label);
            });
            $('button#btn-escolher-endereco').show();
        }
        else
            $('#lista-enderecos').html('Nenhum endereço encontrado. Utilize o botão abaixo para cadastrar seu endereço de entrega. Obrigado.');
    })
    .fail(function(error) {
        if(error.message)
            $('#lista-enderecos').html(error.message);
        else
            $('#lista-enderecos').html('Desculpe, mas não foi possível recuperar seus endereços, por favor, refaça o login e tente novamente novamente.');
    })
    .always(function() {
        $('div.loading-marviin').hide();
    });
}

function process_action(psid)
{
    if(!!$('div.close-window')[0])
    {
        alert('TODO: fechar janela.');
    }
    $('form#form-endereco').validate({
        rules: {
            endereco_entrega: { required: true },
        },
        submitHandler: function(form, e) {
            e.preventDefault();
            if($('button#btn-escolher-endereco').hasClass('nosubmit'))
                return false;
            $('button#btn-escolher-endereco').addClass('nosubmit');
            form.submit();
        }
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
    $('#lista-enderecos').html('Desculpe, mas não consegui recuperar seus endereços, por favor, refaça o login e tente novamente novamente.');
}