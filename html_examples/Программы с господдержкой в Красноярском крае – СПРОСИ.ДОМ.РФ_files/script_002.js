$(document).ready(function () {
  const _contentContainer = '.loadmore_wrap' // контейнер для элементов-материалов
  const _contentElement = '.loadmore_item' // загружаемый элемент-материал
  const _paginationContainer = '.js--pagination' // контейнер с пагинацией
  const _paginationLoadMoreButton = '.js--pagination-load-more' // кнопка пагинации "Загрузить еще"
  const _paginationLink = '.js--pagination-link' // ссылка пагинации

  const $questionAndAnswersSlider = $('.questions-and-answers__slider') // слайдер вопросов-ответов
  const debug = document.location.href.indexOf('clear_cache=Y') !== -1
  $(document).on('click', `${_paginationLoadMoreButton}, ${_paginationLink}`, function (e) {
    if (debug) console.log('Пагинация...')
    e.preventDefault();

    // контейнер блока пагинации
    const $paginationContainer = $(this).closest(_paginationContainer)
    if (debug) console.log('Пагинация: контейнер блока пагинации', $paginationContainer)
    if (!$paginationContainer || $paginationContainer.length === 0) {
      if (debug) console.error(`Пагинация: Не найден контейнер блока пагинации "${_paginationContainer}"`)
      return false
    }
    // контейнер для подгрузки элементов-материалов
    let $contentElementsContainer = $paginationContainer.siblings(_contentContainer)
    if ($contentElementsContainer.length){
      if (debug) console.log('Пагинация: Найден контейнер для подгрузки элементов-материалов, на одном уровне с пагинацией', $contentElementsContainer)
    }
    if (!$contentElementsContainer || $contentElementsContainer.length === 0) {
      $contentElementsContainer = $paginationContainer.closest('.js--news-list-more-wrapper').find(_contentContainer)
      if ($contentElementsContainer.length){
        if (debug) console.log('Пагинация: Найден контейнер для подгрузки элементов-материалов, на одном из уровней выше пагинации', $contentElementsContainer)
      }
    }
    if (!$contentElementsContainer || $contentElementsContainer.length === 0) {
      $contentElementsContainer = $(_contentContainer)
      if ($contentElementsContainer.length){
        if (debug) console.log('Пагинация: Найден контейнер для подгрузки элементов-материалов, первый на всей странице (критично! Если пагинаций больше одной на странице)', $contentElementsContainer)
      }
    }

    if (!$contentElementsContainer || $contentElementsContainer.length === 0) {
      if (debug) console.error(`Пагинация: Не найден контейнер материалов "${_contentContainer}`)
      return false
    }

    let url = ''
    let paginationLoadMore = false
    if ($(this).hasClass(_paginationLoadMoreButton.slice(1))) {
      paginationLoadMore = true;
      url = $(this).attr('data-url')
    } else {
      if ($(this).hasClass(_paginationLink.slice(1))) {
        url = $(this).attr('href')
      }
    }
    if (debug) console.log(`Пагинация: режим - ${paginationLoadMore ? 'добавление следующих материалов' : 'замена материалов выбранной страницей'}`)

    let xml_tag = [];

    if ($questionAndAnswersSlider) {
      for (var i = 0; i <= $questionAndAnswersSlider.length; i++) {
        xml_tag[i] = $($questionAndAnswersSlider[i]).attr('data_tag');
      }
      var num = 6;
    }
    //

    if (debug) console.log(`Пагинация: url: ${url}`)
    if (!paginationLoadMore) {
      // начинаем перематывать в начало контейнера материалов не дожидаясь окончания загрузки контента
      $('body, html').animate({scrollTop: $contentElementsContainer.offset().top}, 800);
    }
    if (url) {
      $paginationContainer.addClass('active')
      $.ajax({
        type: 'GET',
        url: url,
        dataType: 'html',
        // data: {xml_id: xml_tag ? JSON.stringify(xml_tag) : null, num: num},
        success: function (data) {
          const $loadedContentElements = $(data).find(_contentElement);  //  Ищем элементы
          const $loadedPagination = $(data).find(_paginationContainer);//  Ищем навигацию

          if ($loadedContentElements) {
            const $loadedContentElementLikes = $($loadedContentElements).find('.soc-list__icon.soc-list__icon_like');
            var save_likes = JSON.parse(localStorage.getItem('likes'));
            for (let i = 0; i < $loadedContentElementLikes.length; i++) {
              if (save_likes != null) {
                if (save_likes[$($loadedContentElementLikes[i]).attr('data-el-id')] === 'Y') {
                  $($loadedContentElementLikes[i]).addClass('active');
                }
              }
            }

            if (paginationLoadMore) {
              $contentElementsContainer.append($loadedContentElements);   //  Добавляем элементы-материалы в конец контейнера
              history.pushState(null, null, url);
              if (debug) console.log(`Пагинация: добавлено ${$loadedContentElements.length} материалов`)
            } else {
              $contentElementsContainer.html($loadedContentElements) // заменяем элементы-материалы
              // $('body, html').animate({scrollTop: $contentElementsContainer.offset().top}, 800); // перемотка в начало контейнера материалов
              history.pushState(null, null, url);
              if (debug) console.log(`Пагинация: заменено ${$loadedContentElements.length} материалов`, $loadedContentElements)
            }
            if ($loadedPagination) {
              $paginationContainer.replaceWith($loadedPagination) // меняем пагинацию
              // $contentElementsContainer.append($loadedPagination); //  добавляем навигацию следом
              if (debug) console.log(`Пагинация: замена блока пагинации`, $loadedPagination)
            }
            window.fetchLikes();
            const $contentElementShares = $contentElementsContainer.find('.ya-share2');
            if ($contentElementShares) {
              for (i = 0; i < $contentElementShares.length; i++) {
                Ya.share2($contentElementShares[i], {
                  content: {
                    url: $($contentElementShares[i]).attr('data-url')
                  }
                });
              }
            }

            // Подстановка относительного времени материалов
            if (!!$contentElementsContainer[0]) {
              fixElapsedDatetime($contentElementsContainer[0])
            }

          }
          if ($(data).find('.swiper-slide')) {
            window.questionsAndAnswerSliders();
          }
        }
      })
    } else {
      if (debug) console.error('URL не найден');
    }
  });
});
