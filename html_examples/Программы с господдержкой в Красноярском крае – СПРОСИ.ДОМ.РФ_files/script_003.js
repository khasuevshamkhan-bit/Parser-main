function JCSmartFilter(ajaxURL, viewMode, params) {
  this.ajaxURL = ajaxURL;
  this.form = null;
  this.timer = null;
  this.cacheKey = '';
  this.cache = [];
  this.popups = [];
  this.viewMode = viewMode;
  this.reloadMode = 4; //Режим обновления блока фильтра.
  // 1 - классический, с перегрузкой фильтра с паузой
  // 2 - с перегрузкой фильтра c запоминанием открытого select'а
  // 3 - без перегрузки блока фильтра (!! не убираются невозможные значения фильтров!)
  // 4 - с перегрузкой фильтра при закрытии select'а
  // 5 - с частичной перезагрузкой блока фильтра
  if (params && params.SEF_SET_FILTER_URL) {
    this.bindUrlToButton('set_filter', 'catalog');
    this.sef = true;
  }
  if (params && params.SEF_DEL_FILTER_URL) {
    // this.bindUrlToButton('del_filter', params.SEF_DEL_FILTER_URL);
    this.bindUrlToButton('del_filter', 'catalog');
  }
  this.lastInput = null;
  this.lastSelectInput = null; // номер последнего измененного input-а

  /**
   * Сброс фильтров в верхнем блоке
   * @param formResetButton
   */
  this.resetForm = function (formResetButton) {
    log('resetForm', formResetButton)
    if (formResetButton) {
      const form = formResetButton.closest('form')
      log('resetForm, form', form)
      if (form) {
        const inputs = form.querySelectorAll('.js--checkbox-remove');
        if (inputs) {
          for (let input of inputs) {
            removeAllCheckboxes(input);
          }
        }
        this.lastInput = form
        this.close()
      }
    }
  };

  /**
   * Проверяет были ли изменения в селектах и перегружает умный фильтр через close()
   * @param e
   */
  this.checkChanges = function (e) {
    log('@ checkChanges', e)

    let $inputsChanged = $(document).find('input[data-changed="1"]')
    let bInputChanged = $inputsChanged && $inputsChanged.length

    // Если клик за пределами инпутов и были изменения в фильтре, то перезагрузка
    if (e.target.classList.contains('js--window-background') && bInputChanged) {
      this.close($inputsChanged[0])
      return
    }

    let $containerSelect = null;
    if (e.target.classList.contains('js--container-select')) {
      $containerSelect = $(e.target)
    } else {
      if (e.target.classList.contains('js--select-input')) {
        $containerSelect = $(e.target).parents('.js--container-select')
      }
    }
    log('@ checkChanges $containerSelect', $containerSelect)
    const $inputsChangedContainerSelect = $inputsChanged.parents('.js--container-select')
    if ($containerSelect && $containerSelect.length) {
      if (bInputChanged
        && $inputsChangedContainerSelect
        && $inputsChangedContainerSelect.length
        && ($inputsChangedContainerSelect[0].dataset.input !== $containerSelect[0].dataset.input) // если клик был по селекту отличного от того, что был последний раз изменен
      ) {
        log('@ checkChanges inputs Changed !!!!', $inputsChanged)
        log('@ checkChanges $containerSelect this.lastSelectInput', this.lastSelectInput)
        log('@ checkChanges $containerSelect[0].dataset.input', $containerSelect, $containerSelect[0].dataset.input)
        // log('@ checkChanges $inputsChangedContainerSelect', $inputsChangedContainerSelect)
        log('@ checkChanges $inputsChangedContainerSelect[0].dataset.input', $inputsChangedContainerSelect[0].dataset.input)
        this.lastSelectInput = $containerSelect[0].dataset.input
        log('@ checkChanges  - перезагрузка')
        this.close($inputsChanged[0])
        return

      }
      openList($containerSelect[0], e.target)
    }
  }
}

JCSmartFilter.prototype.keyup = function (input) {
  if (!!this.timer) {
    clearTimeout(this.timer);
  }
  this.timer = setTimeout(BX.delegate(function () {
    this.reload(input);
  }, this), 500);
};

JCSmartFilter.prototype.click = function (checkbox) {
  // log('JCSmartFilter click, checkbox', checkbox.tagName, checkbox)
  // log('JCSmartFilter click, this', this)
  // log('JCSmartFilter click, target', this.target)
  let $input = null
  if (checkbox.tagName === 'INPUT') {
    $input = $(checkbox)
  } else {
    $input = $(checkbox).find('input');
  }
  // let property_code = $(checkbox).parent('ul').data('list');
  // let select_title = $(checkbox).closest('.js--select-multiple').find('.js--select-choosen').data('select-title');
  // let current_value = select_title;
  const $parentInput = $input.parents('.js--container-select').find('.js--select-input')
  if ($parentInput && $parentInput.length) {
    $parentInput[0].dataset.changed = 1
  }
  log('JCSmartFilter click', '$input', $input, $parentInput, $parentInput.data('changed'))
  this.lastInput = checkbox;

  // log('JCSmartFilter, click', 'this.lastInput', this.lastInput)
  //если выбран пункт "Все элементы", то сбрасываем все значения у текущего фильтра
  // if (!$input.val()) {
  //   $(checkbox).parent('ul').children().each(function (i, elem) {
  //     if (!!$(elem).data('value')) {
  //       $(elem).find('input').prop('checked', false);
  //     }
  //   });
  //   this.close($(checkbox).closest('.select__list-wrapper')[0]);
  // } else {
  //   $input.prop('checked', !$input.prop('checked'));
  //   if (this.reloadMode === 2)
  //     document.cookie = "open=" + $(checkbox).attr('data-id') + "; path=/; max-age=15";
  // }

  // 3 - без перегрузки блока фильтра (!! не убираются невозможные значения фильтров!)
  // 4 - с перегрузкой фильтра при закрытии select'а
  // 5 - с частичной перезагрузкой блока фильтра
  // if (this.reloadMode === 3 || this.reloadMode === 4 || this.reloadMode === 5) {
  //   //После установки/отмены значений формируем "текущее значение" фильтра, так как он теперь не перезагружается каждый раз
  //   const $current_checked = $(checkbox).parent('ul').children().find('input:checked');
  //   if ($current_checked.length > 1) {
  //     current_value = select_title + ' - Выбрано несколько';
  //   } else {
  //     if ($current_checked.length === 1) {
  //       current_value = $current_checked.closest('li').data('value')
  //     }
  //   }
  //   $(checkbox).closest('.js--select-multiple').find('.js--select-choosen').text(current_value);
  // }
  //
  // if (this.reloadMode === 4) {  // 4 - обновление болка фильтра с перегрузкой фильтра при закрытии select'а
  //   this.lastInput = checkbox;
  // } else {
  //
  //   if (this.reloadMode === 5) {
  //     this.reload(checkbox);
  //   } else {
  //     if (!!this.timer) {
  //       clearTimeout(this.timer);
  //     }
  //
  //     this.timer = setTimeout(BX.delegate(function () {
  //       this.reload(checkbox);
  //     }, this), 500);
  //   }
  // }
};

JCSmartFilter.prototype.order = function (input) {
  document.querySelector('.preloader-block').classList.add('active');
  setTimeout(() => {
      this.cacheKey = '|';
      this.position = BX.pos(input, true);
      this.form = $('form.js--catalog2-filter__form')[0]
      var values = [];
      values[0] = {name: 'ajax', value: 'y'};
      this.gatherInputsValues(values, BX.findChildren(this.form, {'tag': new RegExp('^(input|select)$', 'i')}, true));
      this.sort = $('.catalog-sort__item-wrapper .catalog-sort__item.show').attr('data-href');
      BX.ajax.loadJSON(
        this.ajaxURL,
        this.values2post(values),
        BX.delegate(this.postHandler, this)
      );
    }
    , 1000);

};

JCSmartFilter.prototype.opened = function (list) {
  list.parentNode.classList.add("open");
  list.nextElementSibling.focus();
};
JCSmartFilter.prototype.close = function (el) {
  log('JCSmartFilter.close, this.lastInput', this.lastInput)
  // back.parentNode.classList.remove("open");
  if (!this.lastInput && el !== null) {
    this.lastInput = el.closest('.js--filter-row').querySelector('input')
  }
  let checkbox = this.lastInput;
  this.lastInput = null;
  if (checkbox != null) this.reload(checkbox);
};

JCSmartFilter.prototype.reload = function (input) {
  log('JCSmartFilter.reload, input', input)
  if (this.cacheKey !== '') {
    //Postprone backend query
    if (!!this.timer) {
      clearTimeout(this.timer);
    }
    this.timer = setTimeout(BX.delegate(function () {
      this.reload(input);
    }, this), 1000);
    return;
  }
  this.cacheKey = '|';
  this.position = BX.pos(input, true);
  let formInputs = document.querySelectorAll('.js--catalog2-filter__form input, .js--catalog2-filter__form select, .js--scope_filter input, .js--scope_filter select')
  if (formInputs && formInputs.length > 0) {
    // log('JCSmartFilter.reload formInputs', formInputs)
    let values = [];
    values[0] = {name: 'ajax', value: 'y'};
    this.gatherInputsValues(values, formInputs);
    // log('JCSmartFilter.reload after gatherInputsValues, ', values)
    for (let i = 0; i < values.length; i++)
      this.cacheKey += values[i].name + ':' + values[i].value + '|';

    if (this.cache[this.cacheKey]) {
      this.curFilterinput = input;
      this.postHandler(this.cache[this.cacheKey], true);
    } else {
      this.curFilterinput = input;
      BX.ajax.loadJSON(
        this.ajaxURL,
        this.values2post(values),
        BX.delegate(this.postHandler, this)
      );
    }
    // formInputs.forEach((formInput,i)=>{})
  } else {
    log('JCSmartFilter.reload - не найдены input/select элементы')
  }
};

JCSmartFilter.prototype.updateItem = function (PID, arItem) {
  if (arItem.PROPERTY_TYPE === 'N' || arItem.PRICE) {
    var trackBar = window['trackBar' + PID];
    if (!trackBar && arItem.ENCODED_ID)
      trackBar = window['trackBar' + arItem.ENCODED_ID];

    if (trackBar && arItem.VALUES) {
      if (arItem.VALUES.MIN) {
        if (arItem.VALUES.MIN.FILTERED_VALUE)
          trackBar.setMinFilteredValue(arItem.VALUES.MIN.FILTERED_VALUE);
        else
          trackBar.setMinFilteredValue(arItem.VALUES.MIN.VALUE);
      }

      if (arItem.VALUES.MAX) {
        if (arItem.VALUES.MAX.FILTERED_VALUE)
          trackBar.setMaxFilteredValue(arItem.VALUES.MAX.FILTERED_VALUE);
        else
          trackBar.setMaxFilteredValue(arItem.VALUES.MAX.VALUE);
      }
    }
  } else if (arItem.VALUES) {
    for (var i in arItem.VALUES) {
      if (arItem.VALUES.hasOwnProperty(i)) {
        var value = arItem.VALUES[i];
        var control = BX(value.CONTROL_ID);

        if (!!control) {
          var label = document.querySelector('[data-role="label_' + value.CONTROL_ID + '"]');
          if (value.DISABLED) {
            if (label)
              BX.addClass(label, 'disabled');
            else
              BX.addClass(control.parentNode, 'disabled');
          } else {
            if (label)
              BX.removeClass(label, 'disabled');
            else
              BX.removeClass(control.parentNode, 'disabled');
          }

          if (value.hasOwnProperty('ELEMENT_COUNT')) {
            label = document.querySelector('[data-role="count_' + value.CONTROL_ID + '"]');
            if (label)
              label.innerHTML = value.ELEMENT_COUNT;
          }
        }
      }
    }
  }
};

JCSmartFilter.prototype.postHandler = function (result, fromCache) {
  log('JCSmartFilter.postHandler')


  if (!!result && !!result.ITEMS) {
    for (var popupId in this.popups) {
      if (this.popups.hasOwnProperty(popupId)) {
        this.popups[popupId].destroy();
      }
    }
    this.popups = [];

    for (var PID in result.ITEMS) {
      if (result.ITEMS.hasOwnProperty(PID)) {
        this.updateItem(PID, result.ITEMS[PID]);
      }
    }


    /**
     * Загрузка элементов + обновление всех фильтров (целиком всей динамической часть страницы)
     * @param url
     */
    function customUpdatePage(url, lastSelectInput = null) {
      log('customUpdatePage', url)
      // $('.js--catalog2').load(url + ' ' + '.js--catalog2', function () {
      // });
      $.ajax({
        type: 'GET',
        url: url + (!(lastSelectInput == null || typeof lastSelectInput === undefined) ? (url.includes('?')?'&':'?') + `lastSelectInput=${lastSelectInput}` : ''),
        success: function (data) {
          const oldContent = $('.js--catalog2').html()
          $('.js--catalog2').html($(data).find('.js--catalog2').html())
          if (oldContent != $('.js--catalog2').html()) {
            log('customUpdatePage - контент заменен!!', url)
          }
          reopenSelectInput()
          modals();
        }
      });
    }

    if (result.FILTER_AJAX_URL) {
      log('JCSmartFilter.postHandler - result.FILTER_AJAX_URL', result.FILTER_AJAX_URL)
      url = BX.util.htmlspecialcharsback(result.FILTER_AJAX_URL);

      history.pushState(null, null, BX.util.htmlspecialcharsback(result.FILTER_URL));

      customUpdatePage(url, this.lastSelectInput)

      setTimeout(function () {
        let share = document.querySelectorAll('.ya-share2');
        for (i = 0; i < share.length; i++) {
          Ya.share2(share[i], {
            content: {
              url: $(share[i]).attr('data-url')
            }
          });
        }
        window.fetchLikes();
      }, 1000);
    }
  }

  if (!fromCache && this.cacheKey !== '') {
    this.cache[this.cacheKey] = result;
  }
  this.cacheKey = '';
};

JCSmartFilter.prototype.bindUrlToButton = function (buttonId, url) {
  var button = BX(buttonId);
  if (button) {
    var proxy = function (j, func) {
      return function () {
        return func(j);
      }
    };

    if (button.type == 'submit')
      button.type = 'button';

    BX.bind(button, 'click', proxy(url, function (url) {
      window.location.href = url;
      return false;
    }));
  }
};

JCSmartFilter.prototype.gatherInputsValues = function (values, elements) {
  // log('JCSmartFilter.gatherInputsValues, start values', values)
  // log('JCSmartFilter.gatherInputsValues, elements', elements)
  if (elements) {
    for (var i = 0; i < elements.length; i++) {
      var el = elements[i];
      if (el.disabled || !el.type)
        continue;
      // log('JCSmartFilter.gatherInputsValues, valid element', el)
      switch (el.type.toLowerCase()) {
        case 'text':
        case 'textarea':
        case 'password':
        case 'hidden':
        case 'select-one':
          if (el.value.length)
            values[values.length] = {name: el.name, value: el.value};
          break;
        case 'radio':
        case 'checkbox':
          if (el.checked)
            values[values.length] = {name: el.name, value: el.value};
          break;
        case 'select-multiple':
          for (var j = 0; j < el.options.length; j++) {
            if (el.options[j].selected)
              values[values.length] = {name: el.name, value: el.options[j].value};
          }
          break;
        default:
          break;
      }
    }
  }
};
JCSmartFilter.prototype.search = function (values) {
  var $elements = $('ul.select__list[data-list="' + values.getAttribute('data-list') + '"] li');
  var value = values.value;

  //для регистронезависимого поиска значения
  jQuery.expr[':'].icontains = function (a, i, m) {
    return jQuery(a).text().toUpperCase()
      .indexOf(m[3].toUpperCase()) >= 0;
  };

  $elements.hide();
  $elements.filter(':icontains("' + value + '")').show();
  if ($elements.filter(':icontains("' + value + '")').length == 0) {
    $('ul.select__list[data-list="' + values.getAttribute('data-list') + '"]').append('<li data-item="no_item" class="select__list-item js--select-item">Не найдено</li>');
  } else {
    $('ul.select__list[data-list="' + values.getAttribute('data-list') + '"] li[data-item="no_item"]').remove();
  }
  if (values.value == '') {
    $elements.show();
    $('ul.select__list[data-list="' + values.getAttribute('data-list') + '"] li[data-item="no_item"]').remove()
  }
};
JCSmartFilter.prototype.values2post = function (values) {
  log('JCSmartFilter.values2post, values', values)
  var post = [];
  var current = post;
  var i = 0;

  while (i < values.length) {
    var p = values[i].name.indexOf('[');
    if (p == -1) {
      current[values[i].name] = values[i].value;
      current = post;
      i++;
    } else {
      var name = values[i].name.substring(0, p);
      var rest = values[i].name.substring(p + 1);
      if (!current[name])
        current[name] = [];

      var pp = rest.indexOf(']');
      if (pp == -1) {
        //Error - not balanced brackets
        current = post;
        i++;
      } else if (pp == 0) {
        //No index specified - so take the next integer
        current = current[name];
        values[i].name = '' + current.length;
      } else {
        //Now index name becomes and name and we go deeper into the array
        current = current[name];
        values[i].name = rest.substring(0, pp) + rest.substring(pp + 1);
      }
    }
  }
  return post;
};

JCSmartFilter.prototype.hideFilterProps = function (element) {
  var obj = element.parentNode,
    filterBlock = obj.querySelector("[data-role='bx_filter_block']"),
    propAngle = obj.querySelector("[data-role='prop_angle']");

  if (BX.hasClass(obj, "bx-active")) {
    new BX.easing({
      duration: 300,
      start: {opacity: 1, height: filterBlock.offsetHeight},
      finish: {opacity: 0, height: 0},
      transition: BX.easing.transitions.quart,
      step: function (state) {
        filterBlock.style.opacity = state.opacity;
        filterBlock.style.height = state.height + "px";
      },
      complete: function () {
        filterBlock.setAttribute("style", "");
        BX.removeClass(obj, "bx-active");
      }
    }).animate();

    BX.addClass(propAngle, "fa-angle-down");
    BX.removeClass(propAngle, "fa-angle-up");
  } else {
    filterBlock.style.display = "block";
    filterBlock.style.opacity = 0;
    filterBlock.style.height = "auto";

    var obj_children_height = filterBlock.offsetHeight;
    filterBlock.style.height = 0;

    new BX.easing({
      duration: 300,
      start: {opacity: 0, height: 0},
      finish: {opacity: 1, height: obj_children_height},
      transition: BX.easing.transitions.quart,
      step: function (state) {
        filterBlock.style.opacity = state.opacity;
        filterBlock.style.height = state.height + "px";
      },
      complete: function () {
      }
    }).animate();

    BX.addClass(obj, "bx-active");
    BX.removeClass(propAngle, "fa-angle-down");
    BX.addClass(propAngle, "fa-angle-up");
  }
};

JCSmartFilter.prototype.showDropDownPopup = function (element, popupId) {
  var contentNode = element.querySelector('[data-role="dropdownContent"]');
  this.popups["smartFilterDropDown" + popupId] = BX.PopupWindowManager.create("smartFilterDropDown" + popupId, element, {
    autoHide: true,
    offsetLeft: 0,
    offsetTop: 3,
    overlay: false,
    draggable: {restrict: true},
    closeByEsc: true,
    content: BX.clone(contentNode)
  });
  this.popups["smartFilterDropDown" + popupId].show();
};

JCSmartFilter.prototype.selectDropDownItem = function (element, controlId) {
  this.keyup(BX(controlId));

  var wrapContainer = BX.findParent(BX(controlId), {className: "bx-filter-select-container"}, false);

  var currentOption = wrapContainer.querySelector('[data-role="currentOption"]');
  currentOption.innerHTML = element.innerHTML;
  BX.PopupWindowManager.getCurrentPopup().close();
};

BX.namespace("BX.Iblock.SmartFilter");
BX.Iblock.SmartFilter = (function () {
  /** @param {{
			leftSlider: string,
			rightSlider: string,
			tracker: string,
			trackerWrap: string,
			minInputId: string,
			maxInputId: string,
			minPrice: float|int|string,
			maxPrice: float|int|string,
			curMinPrice: float|int|string,
			curMaxPrice: float|int|string,
			fltMinPrice: float|int|string|null,
			fltMaxPrice: float|int|string|null,
			precision: int|null,
			colorUnavailableActive: string,
			colorAvailableActive: string,
			colorAvailableInactive: string
		}} arParams
   */
  var SmartFilter = function (arParams) {
    if (typeof arParams === 'object') {
      this.leftSlider = BX(arParams.leftSlider);
      this.rightSlider = BX(arParams.rightSlider);
      this.tracker = BX(arParams.tracker);
      this.trackerWrap = BX(arParams.trackerWrap);

      this.minInput = BX(arParams.minInputId);
      this.maxInput = BX(arParams.maxInputId);

      this.minPrice = parseFloat(arParams.minPrice);
      this.maxPrice = parseFloat(arParams.maxPrice);

      this.curMinPrice = parseFloat(arParams.curMinPrice);
      this.curMaxPrice = parseFloat(arParams.curMaxPrice);

      this.fltMinPrice = arParams.fltMinPrice ? parseFloat(arParams.fltMinPrice) : parseFloat(arParams.curMinPrice);
      this.fltMaxPrice = arParams.fltMaxPrice ? parseFloat(arParams.fltMaxPrice) : parseFloat(arParams.curMaxPrice);

      this.precision = arParams.precision || 0;

      this.priceDiff = this.maxPrice - this.minPrice;

      this.leftPercent = 0;
      this.rightPercent = 0;

      this.fltMinPercent = 0;
      this.fltMaxPercent = 0;

      this.colorUnavailableActive = BX(arParams.colorUnavailableActive);//gray
      this.colorAvailableActive = BX(arParams.colorAvailableActive);//blue
      this.colorAvailableInactive = BX(arParams.colorAvailableInactive);//light blue

      this.isTouch = false;

      this.init();

      if ('ontouchstart' in document.documentElement) {
        this.isTouch = true;

        BX.bind(this.leftSlider, "touchstart", BX.proxy(function (event) {
          this.onMoveLeftSlider(event)
        }, this));

        BX.bind(this.rightSlider, "touchstart", BX.proxy(function (event) {
          this.onMoveRightSlider(event)
        }, this));
      } else {
        BX.bind(this.leftSlider, "mousedown", BX.proxy(function (event) {
          this.onMoveLeftSlider(event)
        }, this));

        BX.bind(this.rightSlider, "mousedown", BX.proxy(function (event) {
          this.onMoveRightSlider(event)
        }, this));
      }

      BX.bind(this.minInput, "keyup", BX.proxy(function (event) {
        this.onInputChange();
      }, this));

      BX.bind(this.maxInput, "keyup", BX.proxy(function (event) {
        this.onInputChange();
      }, this));
    }
  };

  SmartFilter.prototype.init = function () {
    var priceDiff;

    if (this.curMinPrice > this.minPrice) {
      priceDiff = this.curMinPrice - this.minPrice;
      this.leftPercent = (priceDiff * 100) / this.priceDiff;

      this.leftSlider.style.left = this.leftPercent + "%";
      this.colorUnavailableActive.style.left = this.leftPercent + "%";
    }

    this.setMinFilteredValue(this.fltMinPrice);

    if (this.curMaxPrice < this.maxPrice) {
      priceDiff = this.maxPrice - this.curMaxPrice;
      this.rightPercent = (priceDiff * 100) / this.priceDiff;

      this.rightSlider.style.right = this.rightPercent + "%";
      this.colorUnavailableActive.style.right = this.rightPercent + "%";
    }

    this.setMaxFilteredValue(this.fltMaxPrice);
  };

  SmartFilter.prototype.setMinFilteredValue = function (fltMinPrice) {
    this.fltMinPrice = parseFloat(fltMinPrice);
    if (this.fltMinPrice >= this.minPrice) {
      var priceDiff = this.fltMinPrice - this.minPrice;
      this.fltMinPercent = (priceDiff * 100) / this.priceDiff;

      if (this.leftPercent > this.fltMinPercent)
        this.colorAvailableActive.style.left = this.leftPercent + "%";
      else
        this.colorAvailableActive.style.left = this.fltMinPercent + "%";

      this.colorAvailableInactive.style.left = this.fltMinPercent + "%";
    } else {
      this.colorAvailableActive.style.left = "0%";
      this.colorAvailableInactive.style.left = "0%";
    }
  };

  SmartFilter.prototype.setMaxFilteredValue = function (fltMaxPrice) {
    this.fltMaxPrice = parseFloat(fltMaxPrice);
    if (this.fltMaxPrice <= this.maxPrice) {
      var priceDiff = this.maxPrice - this.fltMaxPrice;
      this.fltMaxPercent = (priceDiff * 100) / this.priceDiff;

      if (this.rightPercent > this.fltMaxPercent)
        this.colorAvailableActive.style.right = this.rightPercent + "%";
      else
        this.colorAvailableActive.style.right = this.fltMaxPercent + "%";

      this.colorAvailableInactive.style.right = this.fltMaxPercent + "%";
    } else {
      this.colorAvailableActive.style.right = "0%";
      this.colorAvailableInactive.style.right = "0%";
    }
  };

  SmartFilter.prototype.getXCoord = function (elem) {
    var box = elem.getBoundingClientRect();
    var body = document.body;
    var docElem = document.documentElement;

    var scrollLeft = window.pageXOffset || docElem.scrollLeft || body.scrollLeft;
    var clientLeft = docElem.clientLeft || body.clientLeft || 0;
    var left = box.left + scrollLeft - clientLeft;

    return Math.round(left);
  };

  SmartFilter.prototype.getPageX = function (e) {
    e = e || window.event;
    var pageX = null;

    if (this.isTouch && event.targetTouches[0] != null) {
      pageX = e.targetTouches[0].pageX;
    } else if (e.pageX != null) {
      pageX = e.pageX;
    } else if (e.clientX != null) {
      var html = document.documentElement;
      var body = document.body;

      pageX = e.clientX + (html.scrollLeft || body && body.scrollLeft || 0);
      pageX -= html.clientLeft || 0;
    }

    return pageX;
  };

  SmartFilter.prototype.recountMinPrice = function () {
    var newMinPrice = (this.priceDiff * this.leftPercent) / 100;
    newMinPrice = (this.minPrice + newMinPrice).toFixed(this.precision);

    if (newMinPrice != this.minPrice)
      this.minInput.value = newMinPrice;
    else
      this.minInput.value = "";
    /** @global JCSmartFilter smartFilter */
    smartFilter.keyup(this.minInput);
  };

  SmartFilter.prototype.recountMaxPrice = function () {
    var newMaxPrice = (this.priceDiff * this.rightPercent) / 100;
    newMaxPrice = (this.maxPrice - newMaxPrice).toFixed(this.precision);

    if (newMaxPrice != this.maxPrice)
      this.maxInput.value = newMaxPrice;
    else
      this.maxInput.value = "";
    /** @global JCSmartFilter smartFilter */
    smartFilter.keyup(this.maxInput);
  };

  SmartFilter.prototype.onInputChange = function () {
    var priceDiff;
    if (this.minInput.value) {
      var leftInputValue = this.minInput.value;
      if (leftInputValue < this.minPrice)
        leftInputValue = this.minPrice;

      if (leftInputValue > this.maxPrice)
        leftInputValue = this.maxPrice;

      priceDiff = leftInputValue - this.minPrice;
      this.leftPercent = (priceDiff * 100) / this.priceDiff;

      this.makeLeftSliderMove(false);
    }

    if (this.maxInput.value) {
      var rightInputValue = this.maxInput.value;
      if (rightInputValue < this.minPrice)
        rightInputValue = this.minPrice;

      if (rightInputValue > this.maxPrice)
        rightInputValue = this.maxPrice;

      priceDiff = this.maxPrice - rightInputValue;
      this.rightPercent = (priceDiff * 100) / this.priceDiff;

      this.makeRightSliderMove(false);
    }
  };

  SmartFilter.prototype.makeLeftSliderMove = function (recountPrice) {
    recountPrice = (recountPrice !== false);

    this.leftSlider.style.left = this.leftPercent + "%";
    this.colorUnavailableActive.style.left = this.leftPercent + "%";

    var areBothSlidersMoving = false;
    if (this.leftPercent + this.rightPercent >= 100) {
      areBothSlidersMoving = true;
      this.rightPercent = 100 - this.leftPercent;
      this.rightSlider.style.right = this.rightPercent + "%";
      this.colorUnavailableActive.style.right = this.rightPercent + "%";
    }

    if (this.leftPercent >= this.fltMinPercent && this.leftPercent <= (100 - this.fltMaxPercent)) {
      this.colorAvailableActive.style.left = this.leftPercent + "%";
      if (areBothSlidersMoving) {
        this.colorAvailableActive.style.right = 100 - this.leftPercent + "%";
      }
    } else if (this.leftPercent <= this.fltMinPercent) {
      this.colorAvailableActive.style.left = this.fltMinPercent + "%";
      if (areBothSlidersMoving) {
        this.colorAvailableActive.style.right = 100 - this.fltMinPercent + "%";
      }
    } else if (this.leftPercent >= this.fltMaxPercent) {
      this.colorAvailableActive.style.left = 100 - this.fltMaxPercent + "%";
      if (areBothSlidersMoving) {
        this.colorAvailableActive.style.right = this.fltMaxPercent + "%";
      }
    }

    if (recountPrice) {
      this.recountMinPrice();
      if (areBothSlidersMoving)
        this.recountMaxPrice();
    }
  };

  SmartFilter.prototype.countNewLeft = function (event) {
    var pageX = this.getPageX(event);

    var trackerXCoord = this.getXCoord(this.trackerWrap);
    var rightEdge = this.trackerWrap.offsetWidth;

    var newLeft = pageX - trackerXCoord;

    if (newLeft < 0)
      newLeft = 0;
    else if (newLeft > rightEdge)
      newLeft = rightEdge;

    return newLeft;
  };

  SmartFilter.prototype.onMoveLeftSlider = function (e) {
    if (!this.isTouch) {
      this.leftSlider.ondragstart = function () {
        return false;
      };
    }

    if (!this.isTouch) {
      document.onmousemove = BX.proxy(function (event) {
        this.leftPercent = ((this.countNewLeft(event) * 100) / this.trackerWrap.offsetWidth);
        this.makeLeftSliderMove();
      }, this);

      document.onmouseup = function () {
        document.onmousemove = document.onmouseup = null;
      };
    } else {
      document.ontouchmove = BX.proxy(function (event) {
        this.leftPercent = ((this.countNewLeft(event) * 100) / this.trackerWrap.offsetWidth);
        this.makeLeftSliderMove();
      }, this);

      document.ontouchend = function () {
        document.ontouchmove = document.touchend = null;
      };
    }

    return false;
  };

  SmartFilter.prototype.makeRightSliderMove = function (recountPrice) {
    recountPrice = (recountPrice !== false);

    this.rightSlider.style.right = this.rightPercent + "%";
    this.colorUnavailableActive.style.right = this.rightPercent + "%";

    var areBothSlidersMoving = false;
    if (this.leftPercent + this.rightPercent >= 100) {
      areBothSlidersMoving = true;
      this.leftPercent = 100 - this.rightPercent;
      this.leftSlider.style.left = this.leftPercent + "%";
      this.colorUnavailableActive.style.left = this.leftPercent + "%";
    }

    if ((100 - this.rightPercent) >= this.fltMinPercent && this.rightPercent >= this.fltMaxPercent) {
      this.colorAvailableActive.style.right = this.rightPercent + "%";
      if (areBothSlidersMoving) {
        this.colorAvailableActive.style.left = 100 - this.rightPercent + "%";
      }
    } else if (this.rightPercent <= this.fltMaxPercent) {
      this.colorAvailableActive.style.right = this.fltMaxPercent + "%";
      if (areBothSlidersMoving) {
        this.colorAvailableActive.style.left = 100 - this.fltMaxPercent + "%";
      }
    } else if ((100 - this.rightPercent) <= this.fltMinPercent) {
      this.colorAvailableActive.style.right = 100 - this.fltMinPercent + "%";
      if (areBothSlidersMoving) {
        this.colorAvailableActive.style.left = this.fltMinPercent + "%";
      }
    }

    if (recountPrice) {
      this.recountMaxPrice();
      if (areBothSlidersMoving)
        this.recountMinPrice();
    }
  };

  SmartFilter.prototype.onMoveRightSlider = function (e) {
    if (!this.isTouch) {
      this.rightSlider.ondragstart = function () {
        return false;
      };
    }

    if (!this.isTouch) {
      document.onmousemove = BX.proxy(function (event) {
        this.rightPercent = 100 - (((this.countNewLeft(event)) * 100) / (this.trackerWrap.offsetWidth));
        this.makeRightSliderMove();
      }, this);

      document.onmouseup = function () {
        document.onmousemove = document.onmouseup = null;
      };
    } else {
      document.ontouchmove = BX.proxy(function (event) {
        this.rightPercent = 100 - (((this.countNewLeft(event)) * 100) / (this.trackerWrap.offsetWidth));
        this.makeRightSliderMove();
      }, this);

      document.ontouchend = function () {
        document.ontouchmove = document.ontouchend = null;
      };
    }

    return false;
  };
  return SmartFilter;
})();


/**
 * Открывает селект, который был открыт до перегрузки умного фильтра
 * (был отмечен .js--was-opened)
 */
function reopenSelectInput() {
  const selectInputWasOpened = document.querySelector('.js--was-opened')
  log('@ reopenSelectInput')
  if (selectInputWasOpened) {
    log('@ reopenSelectInput selectInputWasOpened', selectInputWasOpened)
    openList(selectInputWasOpened)
  }
}

var log = function () {
  const searchParams = new URLSearchParams(window.location.search);
  if (searchParams.has('clear_cache')) {
  console.log(...arguments)
  }
}
