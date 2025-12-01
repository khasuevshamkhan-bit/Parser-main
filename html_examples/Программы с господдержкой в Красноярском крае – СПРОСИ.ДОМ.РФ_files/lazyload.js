/**
 * Отложенная загрузка вебформы при скроллинге к месту ее вывода
 * @param webFormPlaceholderTarget  - целевой объект для загрузки вебформы
 * @param webFormCode               - символьный код вебформы
 * @param webformTemplate           - bitrix-шаблон вебформы для bitrix:form.result.new
 */
function lazyLoadWebform(webFormPlaceholderTarget, webFormCode, webformTemplate, webFormParams = null) {
  var observerWebFormLoad = new IntersectionObserver(function (entries, observer) {
    // console.log(entries);
    for (entry of entries) {
      if (entry.isIntersecting) {
        console.log(`-- Loading webform ${webFormCode}`);
        let webformPageFrom = window.location.pathname;
        let webformUrlFrom = window.location.pathname + window.location.search;
        let query = `/local/ajax/get_webform.php?webFormCode=${webFormCode}&webformTemplate=${webformTemplate}&webformPageFrom=${webformPageFrom}&webformUrlFrom=${webformUrlFrom}`;
        if (webFormParams){
          query += `&webformParams=${encodeURIComponent(webFormParams)}`;
        }
        // console.log('webform query', query)
        $.ajax({
          url: query,
          success: function (result) {
            // console.log({result});
            if (!!result) {
              $(entry.target).html(result);
              // phoneMask();
              // selectsInit();
              modals();
              clickSelectItem();
              openListDirectory();
              closeSelectList();
              closeSelectListNoneOpenlistBackground();

             window.universalForm();
              svgHandWritingFixed(webFormPlaceholderTarget)
            } else {
              console.warn(`Webform <${webFormCode}> not found`);
            }
            observer.unobserve(entry.target);
            observer.disconnect;
          },
          error: function (error) {
            console.warn(`Loading webform <${webFormCode}> failed`, error);
          }
        });
      }
    }
  });
  observerWebFormLoad.observe(webFormPlaceholderTarget);
}

/**
 * Отложенная загрузка модальной вебформы при клике на кнопку открытия модальных вебформ
 * @param webFormPlaceholderTarget  - целевой объект для загрузки вебформы
 * @param webFormCode               - символьный код вебформы
 * @param webformTemplate           - bitrix-шаблон вебформы для bitrix:form.result.new
 */
function lazyLoadModalWebForm(webFormPlaceholderTarget, webFormCode, webformTemplate,webFormParams = null,webformId = null) {
  console.log(`-- Loading modal webform ${webFormCode}`);
  let webformPageFrom = window.location.pathname;
  let webformUrlFrom = window.location.pathname + window.location.search;
  let query = `/local/ajax/get_webform.php?webFormCode=${webFormCode}&webformTemplate=${webformTemplate}&webformPageFrom=${webformPageFrom}&webformUrlFrom=${webformUrlFrom}`
  if (webFormParams){
    query += `&webformParams=${encodeURIComponent(webFormParams)}`;
  }
  $.ajax({
    url: query,
    success: function (result) {
      // console.log({result});
      if (!!result) {
        $(webFormPlaceholderTarget).html(result);
        modals();
        clickSelectItem();
        openListDirectory();
        closeSelectList();
        closeSelectListNoneOpenlistBackground();

        if (!!webformId) {
          const modalButton = document.querySelector(`.js--modal-opener[data-modal="#${webformId}"]`);
          if (!!modalButton){
            modalButton.click();
          }
        }
      } else {
        console.warn(`Modal Webform <${webFormCode}> not found`);
      }
    },
    error: function (error) {
      console.warn(`Loading modal webform <${webFormCode}> failed`, error);
    }
  });
}

/**
 * Поиск всех LazyLoad-вебформ для последующей их загрузки при скроллинге
 */
document.addEventListener('DOMContentLoaded', function () {
  let lazyLoadModalWebformsLoaded = false;
  const lazyLoadWebforms = document.querySelectorAll('.js-lazyload-webform');
  if (lazyLoadWebforms.length) {
    // console.log(`Found ${lazyLoadWebforms.length} lazyload webforms`);
    lazyLoadWebforms.forEach(function (el) {
      if (el.dataset?.code && el.dataset?.template) {
        let webFormParams = el.dataset?.params ?? null;
        // console.log(`Found lazyload webform <${el.dataset.code}>`);
        lazyLoadWebform(el, el.dataset.code, el.dataset.template, webFormParams)
      }
    })
  }
  const lazyModalLoadWebforms = document.querySelectorAll('.js-lazyload-modal-webform');
  if (lazyModalLoadWebforms.length) {
    // console.log(`Found ${lazyModalLoadWebforms.length} modal lazyload webforms`);
    const modalWebformButtons = document.querySelectorAll('.js--modal-opener');
    let modalWebformIds = [];
    if (modalWebformButtons.length)
      modalWebformButtons.forEach(function (modalBtn) {
        if (modalBtn.dataset?.modal)
          modalWebformIds.push(modalBtn.dataset.modal.replace('#', ''));
      });
    const modalBtnWrapper = document.querySelector('.js-lazyload-modal-webform-buttons')
    // const modalBtnWrapper = document.querySelector(`/*.js-lazyload-modal-webform-buttons [data-modal="#${webFormPlaceholderTarget.id}"]*/`)
    if (modalBtnWrapper)
      modalBtnWrapper.addEventListener('click', () => {
        if (!lazyLoadModalWebformsLoaded) {
          lazyModalLoadWebforms.forEach(function (el) {
            if (el.dataset?.code && el.dataset?.template) {
              if (modalWebformIds.length && modalWebformIds.includes(el.dataset?.id)) {
                let webFormParams = el.dataset?.params ?? null;
                // console.log(`Found modal lazyload webform <${el.dataset.code}>`);
                lazyLoadModalWebForm(el, el.dataset.code, el.dataset.template,webFormParams,el.dataset?.id);
              }
            }
          })
          lazyLoadModalWebformsLoaded = true;
        }
        // phoneMask();
        // modals();
        // selectsInit();
        modals();
        clickSelectItem();
        openListDirectory();
        closeSelectList();
        closeSelectListNoneOpenlistBackground();
        window.universalForm();
      });

  }
});

function svgHandWritingFixed(webFormPlaceholderTarget){
  if (webFormPlaceholderTarget) {
    const _svg_hand_writing = webFormPlaceholderTarget.querySelector('.js--svg-hand-writing')
    if (_svg_hand_writing) {
      _svg_hand_writing.classList.add('active');
    }
  }
}
