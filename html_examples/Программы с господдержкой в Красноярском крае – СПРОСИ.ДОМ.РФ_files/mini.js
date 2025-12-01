document.addEventListener("DOMContentLoaded", function() {
  //обработка лайков
  const likes = $('a.soc-list__icon.soc-list__icon_like');
  const defaultType = '1';
  let save_likes = [];
  if (localStorage.getItem('likes') !== null) {
    save_likes = JSON.parse(localStorage.getItem('likes'));
    if (!Array.isArray(save_likes)) {
      save_likes = [];
    }
  }

  if (save_likes.length) {
    for (let i = 0; i < likes.length; i++) {
      const elementType = $(likes[i]).attr('data-el-type') || defaultType;
      if (save_likes.some(e => e.id === $(likes[i]).attr('data-el-id') && e.type === elementType)) {
        $(likes[i]).addClass('active');
      }
    }
  }
  $('.page-wrap').on('click', '.soc-list__icon_like', function (e) {
    if (!$(e.target).closest('.soc-list__icon_like').hasClass('active')) {
      ajax($(e.target).closest('.soc-list__icon_like')[0]);
    }
  });

  $('.page-wrap').on('click', '.ya-share2.soc-list__icon', function (e) {
    let elem = $(e.target).closest('.soc-list__icon_share')
    //console.log($(e.target));
    share(elem.attr('data-id'), elem.attr('data-el-type'));
  });
  //обработка просмотров
  const viewElem = document.getElementById('section_id');
  if (viewElem) {
    const id = viewElem.value;
    const elementType = viewElem.getAttribute('data-el-type') || defaultType;

    const viewItem = {id: id, type: elementType};

    let currentValue = [];
    if (localStorage.getItem('views') !== null) {
      currentValue = JSON.parse(localStorage.getItem('views'));
      if (!Array.isArray(currentValue)) {
        currentValue = [];
      }
    }

    if (!currentValue.some(e => e.id === id && e.type === elementType)) {
      currentValue.push(viewItem);
      const dataType = viewElem.getAttribute('data-type') || null;
      ajaxViews(id, elementType, dataType)
    }
    localStorage.setItem('views', JSON.stringify(currentValue));
  }

  function share(id, type = defaultType) {

    BX.ajax({
      url: '/local/components/dev/likes/templates/mini/ajax.php',
      data: {
        element_id : id,
        type : type,
        share : 'Y'
      },
      method: 'POST',
      dataType: 'html',
      timeout: 30,
      async: true,
      processData: true,
      scriptsRunFirst: true,
      emulateOnload: true,
      start: true,
      cache: false,
      onsuccess: function(data){
        let count = Number($('.ya-share2.soc-list__icon[data-id="'+id+'"]').next().html())+1;
        $('.ya-share2.soc-list__icon[data-id="'+id+'"]').next().html(count);
      },
      onfailure: function(){

      }
    });
  }

  /**
   *
   * @param id - id элемента или раздела
   * @param elementType 1 - элемент, 2 - раздел
   * @param dataType тип страницы (question/null)
   */
  function ajaxViews(id, elementType, dataType = null) {
    BX.ajax({
      url: '/local/ajax/views.php',
      data: {id : id, element_type: elementType, data_type: dataType },
      method: 'POST',
      dataType: 'html',
      timeout: 30,
      async: true,
      processData: true,
      scriptsRunFirst: true,
      emulateOnload: true,
      start: true,
      cache: false,
      onsuccess: function(data){
        //console.log(data);
      },
      onfailure: function(){

      }
    });
  }
  function ajax(e) {
    const id = e.getAttribute('data-el-id');
    const type = e.getAttribute('data-el-type') || defaultType;
    BX.ajax({
      url: '/local/components/dev/likes/templates/mini/ajax.php',
      data: {
        element_id : id,
        type : type,
        likes : localStorage.getItem('likes') ?? JSON.stringify([]),
      },
      method: 'POST',
      dataType: 'html',
      timeout: 30,
      async: true,
      processData: true,
      scriptsRunFirst: true,
      emulateOnload: true,
      start: true,
      cache: false,
      onsuccess: function(data){

        let currentValue = [];
        if (localStorage.getItem('likes') !== null) {
          currentValue = JSON.parse(localStorage.getItem('likes'));
          if (!Array.isArray(currentValue)) {
            currentValue = [];
          }
        }

        const like = {id: data, type: type};
        if (!currentValue.some(e => e.id === data && e.type === type)) {
          currentValue.push(like);
          const count = Number(e.nextSibling.innerHTML)+1;
          $(e).next('.soc-list__counter').text(count);
          $(e).addClass('active');
        }
        localStorage.setItem('likes', JSON.stringify(currentValue));
      },
      onfailure: function(){

      }
    });
  }
  function isEmptyObject(obj) {
    for (var i in obj) {
      if (obj.hasOwnProperty(i)) {
        return false;
      }
    }
    return true;
  }
});
