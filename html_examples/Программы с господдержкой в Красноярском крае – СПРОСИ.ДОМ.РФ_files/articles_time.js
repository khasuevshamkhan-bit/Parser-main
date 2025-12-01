/**
 * Подстановка относительного времени материалов
 */


document.addEventListener('DOMContentLoaded', function () {
  fixElapsedDatetime()
});

/**
 * Подстановка относительного времени материалов
 * @param container - контейнер с элементами, для вызова после динамически измененного контента (ajax)
 */
function fixElapsedDatetime(container = null) {
  try {
    if (container === null) {
      container = document
    }
    const timestamppublishedItems = container.querySelectorAll('[data-timestamppublished]')
    if (timestamppublishedItems.length) {
      // console.log('fixElapsedDatetime() timestamppublishedItems', timestamppublishedItems);
      timestamppublishedItems.forEach(function (el) {
        if (el.dataset?.timestamppublished) {

          let timestatmpNow = new Date()
          let timestamppublished = new Date(el.dataset.timestamppublished * 1000)

          if (
            (timestatmpNow.getFullYear() === timestamppublished.getFullYear())
            && (timestatmpNow.getMonth() === timestamppublished.getMonth())
            && (timestatmpNow.getDate() === timestamppublished.getDate())
          ) {

            /**
             * Склоняет слова по числу
             * @param number
             * @param words
             * @returns {*}
             */
            const declOfNum =  function (number, words) {
              return words[(number % 100 > 4 && number % 100 < 20) ? 2 : [2, 0, 1, 1, 1, 2][(number % 10 < 5) ? Math.abs(number) % 10 : 5]];
            }

            let timeDiffSeconds = Math.round((timestatmpNow - timestamppublished) / 1000)
            // console.log('fixElapsedDatetime() timeDiffSeconds',timeDiffSeconds)
            let elapsedDatetimeString = 'сегодня';

            // Если указано время публикации, а не просто дата с временем 00:00:00
            if ((timestamppublished.getHours()>0) || (timestamppublished.getMinutes()>0) || (timestamppublished.getSeconds()>0)) {
              if (timeDiffSeconds < 60) {
                elapsedDatetimeString = 'сейчас'
              } else if (timeDiffSeconds < (60 * 60)) {
                let timeElapsed = Math.floor(timeDiffSeconds / 60);
                elapsedDatetimeString = timeElapsed + ' ' + declOfNum(timeElapsed, ['минуту', 'минуты', 'минут']) + ' назад'
              } else {
                let timeElapsed = Math.floor(timeDiffSeconds / 60 / 60);
                elapsedDatetimeString = timeElapsed + ' ' + declOfNum(timeElapsed, ['час', 'часа', 'часов']) + ' назад'
              }
            }
            el.innerText = elapsedDatetimeString;
          }
        }
      })
    }
  } catch (e) {
    console.warn(e)
  }
}
