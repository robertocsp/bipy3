$(function() {
    if($('form#form-criarconta')[0])
    {
        var SPMaskBehavior = function (val) {
          return val.replace(/\D/g, '').length === 11 ? '(00) 00000-0000' : '(00) 0000-00009';
        },
        spOptions = {
          onKeyPress: function(val, e, field, options) {
              field.mask(SPMaskBehavior.apply({}, arguments), options);
          }
        };

        $('#cpf').mask('000.000.000-00');
        $('#telefone').mask(SPMaskBehavior, spOptions);

        $('form#form-criarconta').validate({
            rules: {
                nome: { required: true },
                cpf: { required: true },
                telefone: { required: true },
                email: { required: true },
                termos: { required: true },
            }
        });
        $.extend(
            $.validator.messages, {
                required: 'Campo obrigatório.',
                email: 'E-mail inválido.'
            }
        );
    }
});

function process_action(psid)
{
    $('input#psid').val(psid);
}

function error_handler(err)
{
    $('#form-criarconta').find('label').remove();
    $('#form-criarconta').find('div').remove();
    var error_form_group = $('<div></div>')
                            .attr('class', 'form-group');
    var error_col = $('<div></div>')
                     .attr('class', 'col-xs-12');
    error_col.append($('<label></label>').text('Acesso inválido, esta página só pode ser acessada a partir do Messenger. Se você acessou a partir do Messenger, por favor, tente novamente.'));
    error_form_group.append(error_col);
    $('#form-criarconta').append(error_form_group);
}