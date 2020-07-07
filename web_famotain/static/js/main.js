$(function(){
    var form = $("#order-form");
	$("#wizard").steps({
        headerTag: "h4",
        bodyTag: "section",
        transitionEffect: "fade",
        // enableAllSteps: true,
        transitionEffectSpeed: 500,
        onStepChanging: function (event, currentIndex, newIndex) {
            form.validate({
              ignore: ":disabled,:hidden"
            });
            valid =  form.valid();
            if (!valid){
                return valid;
            }
            if ( newIndex === 1 ) {
                $('.steps ul').addClass('step-2');
            } else {
                $('.steps ul').removeClass('step-2');
            }
            if ( newIndex === 2 ) {
                $('.steps ul').addClass('step-3');
            } else {
                $('.steps ul').removeClass('step-3');
            }
            if ( newIndex === 3 ) {
                $('.steps ul').addClass('step-4');
                // $('.actions ul').addClass('step-last');
            } else {
                $('.steps ul').removeClass('step-4');
                // $('.actions ul').removeClass('step-last');
            }
            $('#wizard-t-' + newIndex).parent().addClass('checked');
            $('#wizard-t-' + newIndex).parent().prevAll().addClass('checked');
            $('#wizard-t-' + newIndex).parent().nextAll().removeClass('checked');
            return true;
        },
        labels: {
            finish: "Submit",
            next: "Next",
            previous: "Previous"
        },
        onFinishing: function (event, currentIndex)
        {
            form.validate({
              ignore: ":disabled"
            });
            return form.valid();
        },
        onFinished: function (event, currentIndex){
            form.submit();
        }
    });
    // Custom Button Jquery Steps
    $('.forward').click(function(){
    	$("#wizard").steps('next');
    })
    $('.backward').click(function(){
        $("#wizard").steps('previous');
    })
    // Checkbox
    $('.checkbox-circle label').click(function(){
        $('.checkbox-circle label').removeClass('active');
        $(this).addClass('active');
    })

    $('#input-packaging').on('change', function(){
        if ($(this).val() === '-' || $(this).val() === 'TC'){
            $('#form-packing').addClass('form-hide');
        } else {
            $('#form-packing').removeClass('form-hide');
        }
    })
})
