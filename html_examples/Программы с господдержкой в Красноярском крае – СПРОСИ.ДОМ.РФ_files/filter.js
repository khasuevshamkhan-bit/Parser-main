/* eslint-disable */

let input=[]

function inputPlaceHolder() {
  const parent = document.querySelector('.js--parent-filter');
  if (parent) {
    const array_input = parent.querySelectorAll('.js--checkbox-selected .js--select-input');
    for (let i=0; i<array_input.length; i++) {
      let object_input= {};
      const place_holder = array_input[i].getAttribute('placeholder');
      object_input.active = false;
      object_input.placeholder = place_holder;
      object_input.input = [];
      input.push(object_input)
    }
  }
}

if (document.readyState !== 'loading') {
  inputPlaceHolder();
} else {
  document.addEventListener('DOMContentLoaded', function () {
    inputPlaceHolder();
  });
}
// document.addEventListener('DOMContentLoaded', function() {
//   inputPlaceHolder();
// })


function placeholderInput() {
  const parent = document.querySelector('.js--parent-filter');
  if (parent) {
    const array_input = parent.querySelectorAll('.js--checkbox-selected .js--select-input');
    for (let i=0; i<array_input.length; i++) {
      array_input[i].setAttribute('placeholder',`${input[i].placeholder}`)
    }
  }
}
// placeholderInput();

function substitutingDataFromArray(element,data){
  if (element.classList.contains('js--checkbox-selected')) {
    if (input[data].input.length===0){
      // alert('1')
      element.querySelector('.js--select-input').value = '';
      element.querySelector('.js--select-input').setAttribute('data-search', '');
    }
    else if (input[data].input.length===1){
      // alert('2')
      element.querySelector('.js--select-input').value = input[data].input;
      element.querySelector('.js--select-input').setAttribute('data-search', input[data].input);
    }
    else {
      // alert('3')
      element.querySelector('.js--select-input').value = 'Выбрано несколько';
      element.querySelector('.js--select-input').setAttribute('data-search', 'Выбрано несколько');
    }

    if (input[data].input.length>0 && element.closest('.js--filter-row')) {
      element.closest('.js--filter-row').classList.add('active')
    }
  }
}

function selectChecBox(el) {
  const element = el.currentTarget;
  const parent = element.closest('.js--container-select');
  let input_massive=[]
  let data_input;
  if(element.closest('.js--select-list') && element.closest('.js--select-list').hasAttribute('data-input')){
    data_input = element.closest('.js--select-list').getAttribute('data-input');
    data_input=parseInt(data_input)
  }
  else {
    data_input='undefined'
  }

  if (element.checked){
    let { value } = element.closest('.js--select-item-checkbox').dataset;
    let text = element.closest('.js--select-item-checkbox').querySelector('label').textContent;
    text = text.trim();
    if(data_input!=='undefined'){
      input[data_input].input.push(text)
    }

  }
  else {
    let text = element.closest('.js--select-item-checkbox').querySelector('label').textContent;
    text = text.trim();
    let index = input[data_input].input.indexOf(text);
    if (index !== -1 && data_input!=='undefined') {
      input[data_input].input.splice(index, 1);
    }
  }
}

// Переделал, так как изменился механизм вызова функции открытия/закрытия селектов (Artem.Subochev@domrf.ru)
function openList(element,e_target) {
  const parent = element.closest('.js--filter-row');
  const container = element.closest('.js--parent-filter');
  const array__select = container.querySelectorAll('.js--container-select.open')


  // Убрал пока закрытие селекта, иначе при клике в поле поиска для ввода значения селект закрывался (Artem.Subochev@domrf.ru)
  // if (element.classList.contains('open') && element.tagName!=='INPUT' && element.tagName!=='LABEL' && element.tagName!=='BUTTON') {
  //   element.querySelector('.js--select-input').blur();
  //
  //   if(parent && parent.querySelector('.js--window-background')) {
  //     parent.querySelector('.js--window-background').setAttribute('style','display:none')
  //   }
  //   element.classList.remove('open');
  //   element.setAttribute('style','z-index:11;')
  //
  //
  //
  //   //если выбор чекбоксов, то проверяется наличие класса js--checkbox-selected и если он есть,
  //   //то когда поле с выбором закрывается, выбранные значения подставляются в поле
  //   //если выбрано несколько значений, то в поле пявляется надпись Выбрано несколько
  //   let data_input
  //   if(element.querySelector('.js--select-list') && element.querySelector('.js--select-list').hasAttribute('data-input')){
  //     data_input = element.querySelector('.js--select-list').getAttribute('data-input');
  //     data_input=parseInt(data_input);
  //     substitutingDataFromArray(element,data_input);
  //     substitutingDataFromArray(element,data_input);
  //   }
  //   else {
  //     substitutingDataFromArray(element,0);
  //   }
  //     if (input[data_input]){
  //      input[data_input].active=false
  //     }
  //
  //   element.querySelector('.js--select-input').setAttribute('placeholder',`${input[data_input].placeholder}`);
  //
  // }
  //
  // else


  if (!element.classList.contains('open') && element.tagName!=='LABEL' && element.tagName!=='BUTTON') {
    //Закрываю все открытые окна
    for (let item of array__select) {
      item.classList.remove('open')
      item.setAttribute('style','z-index:11;')
      if (item.hasAttribute('data-input')) {
        substitutingDataFromArray(item,parseInt(item.getAttribute('data-input')));
        if (item.classList.contains('js--checkbox-selected')) {
          input[parseInt(item.getAttribute('data-input'))].active=false
          if (item.querySelector('input')) {
            item.querySelector('input').setAttribute('placeholder',`${input[parseInt(item.getAttribute('data-input'))].placeholder}`);
          }
        }
      }
    }
    //вызов метода сохранения данных в поле с выб.log ранным значением при закрытии окна
    if (element.querySelector('.js--select-input')) {
      element.querySelector('.js--select-input').value = '';
    }
    sampleliveSearch(element.querySelector('.js--select-input'));
    if(parent && parent.querySelector('.js--window-background')) {
      parent.querySelector('.js--window-background').setAttribute('style','display:block')
    }
    if(element.closest('.js--filter-row')) {
      element.closest('.js--filter-row').classList.remove('active')
    }

    if (element.classList.contains('js--checkbox-selected')) {
      let data_input;
      if (element.hasAttribute('data-input')) {
        data_input = element.getAttribute('data-input');
        data_input=parseInt(data_input);
      }
      if (input[data_input]){
       input[data_input].active=true
      }

      element.querySelector('.js--select-input').setAttribute('placeholder','Поиск...');
      element.setAttribute('style','z-index:14;')
    }

    setTimeout(() => {
      element.classList.add('open');
    },100)
  }
  if (element.classList.contains('open') && !e_target.classList.contains('js--select-input')) {
    if (document.querySelector('.js--window-background')) {
      document.querySelector('.js--window-background').click();
    }
  }

  if (element.querySelector('.js--input__error_required')) {
    element.querySelector('.js--input__error_required').remove();
  }
  if (element.classList.contains('.input_error')) {
    element.classList.remove('.input_error');
  }
  element.classList.remove('input_error');
}

function clickBackground(el){
  const element = el.currentTarget;
  const parent = element.closest('.js--filter-row');
  element.setAttribute('style','display:none')
  if (parent && parent.querySelector('.js--container-select')) {
    parent.querySelector('.js--container-select').classList.remove('open');
    parent.querySelector('.js--container-select').setAttribute('style','z-index:11;')

    let data_input
    if(parent.querySelector('.js--select-list') && parent.querySelector('.js--select-list').hasAttribute('data-input')){
      data_input = parent.querySelector('.js--select-list').getAttribute('data-input');
      data_input=parseInt(data_input);
      substitutingDataFromArray(parent.querySelector('.js--container-select'),data_input)
    }
      if (input[data_input]){
       input[data_input].active=false
      }

    parent.querySelector('.js--select-input').setAttribute('placeholder',`${input[data_input].placeholder}`);
  }
}

function removeAllCheckboxes(el) {
  let element = el.currentTarget;

  // Для вызова из кнопки общего Сброса формы (Artem.Subochev@domrf.ru)
  if(el && (element== null || typeof element === undefined)){
    element = el
  }
  const parent = element.closest('.js--filter-row').querySelector('.js--checkbox-remove');
  // console.log('removeAllCheckboxes',element,parent)
  if (parent && parent.querySelector('.js--select-list-remove-checkbox')) {
    const array_chekcbox = parent.querySelector('.js--select-list-remove-checkbox').querySelectorAll('input[type="checkbox"]:checked');
    for (let item of array_chekcbox) {
      item.checked = false;
    }
    if (parent.querySelector('.js--select-list') && parent.querySelector('.js--select-list').hasAttribute('data-input')) {
      let data_input
      data_input = parent.querySelector('.js--select-list').getAttribute('data-input');
      data_input=parseInt(data_input);
      input[data_input].input=[]
      substitutingDataFromArray(parent,data_input);
    }

    // Ставим отметку, что input был изменен, для последующей ajax-перезагрузки, при клике на другой input (Artem.Subochev@domrf.ru)
    const selectInput = parent.querySelector('.js--select-input')
    if(selectInput){
      selectInput.dataset.changed = 1
    }
  }
  return true
}

//Поиск...
function liveSearch(el) {
  const input_search = el.currentTarget;
  sampleliveSearch(input_search)
}
function sampleliveSearch(input_search) {
  const parent = input_search.closest('.js--search-container');
  if (parent) {
    const val = input_search.value;
    // eslint-disable-next-line camelcase
    const array_label = parent.querySelectorAll('.js--searh-item');
    for (let i = 0; i < array_label.length; i++) {
      const reg = new RegExp(val, 'gi');
      const text = array_label[i].textContent;

      if (!array_label[i].classList.contains('js--select-item-checkbox')){
        const box = array_label[i];
        let text_box = box.innerHTML;
        text_box = text.replace(/(<span class="highlight">|<\/span>)/gim, '');
        box.innerHTML = text_box.replace(reg, '<span class="highlight">$&</span>');
      }

      if (text.match(reg)) {
        array_label[i].style.display = 'block';
        array_label[i].classList.add('active');
      } else {
        array_label[i].style.display = 'none';
        array_label[i].classList.remove('active');
      }
    }
    // eslint-disable-next-line max-len,camelcase
    const array_label_active = parent.querySelectorAll('.js--searh-item.active');
    // eslint-disable-next-line camelcase
    const array_error = parent.querySelectorAll('.js--search-error');
    if (array_label_active.length === 0) {
      // eslint-disable-next-line no-shadow,no-undef,camelcase
      const wrapper_list = parent.querySelector('.js--select-list');

      if (array_error.length === 0) {
        // eslint-disable-next-line camelcase
        const element_error = document.createElement('li');
        // eslint-disable-next-line max-len
        element_error.classList.add('select__list-item', 'js--search-error', 'error');
        element_error.innerHTML += 'Ничего не найдено';
        wrapper_list.append(element_error);
      }
    } if (array_label_active.length !== 0 && array_error.length !== 0) {
      // eslint-disable-next-line no-undef
      parent.querySelector('.js--search-error').remove();
    }
  }
}


//Фильтер регион

function openListDirectory(el) {
  const element = el.currentTarget;
  const parent = element.closest('.js--openlist-container');

  const windowBackground = parent.querySelector('.js--openlist-background');
  parent.classList.add('open');
  if (windowBackground) {
    windowBackground.style.display = 'block';
  }

  // закрытие окна
  if (windowBackground) {
    windowBackground.onclick = () => {
      parent.classList.remove('open');
      windowBackground.style.display = 'none';
    };
  }
}

function removeClassActiveItem(element,parent) {
  const SelectItemActive = parent.querySelector('.js--openlist-item-filter.active');
  SelectItemActive.classList.remove('active');
}
function choiceActiveItem(element,parent) {
  const result = parent.querySelector('.js--openlist-btn-filter p');
  element.classList.add('active');
  let content = element.textContent;
  content = content.replace(/^\s\s*/, '').replace(/\s\s*$/, '')
  result.innerHTML = content
}
//Закрываю окно
function closeList(element,parent) {
  parent.classList.remove('open')
  parent.querySelector('.js--openlist-background').style.display='none';
}
function clickSelectItem(el) {
  const element = el.currentTarget;
  const mainContainer = element.closest('.js--openlist-container')
  removeClassActiveItem(element, mainContainer);
  choiceActiveItem(element, mainContainer);
  closeList(element, mainContainer);
}
