$(document).ready(function() {
	//output
	item_id = "item-" + (new Date).getTime();
	$terminal.print($('<div id="'+item_id+'">Globe here.</div>'));

	$.getScript("/js/libs/ThreeWebGL.js").done(function(script, textStatus) {
		$.getScript("/js/libs/ThreeExtras.js").done(function(script, textStatus) {
			$.getScript("/js/libs/RequestAnimationFrame.js").done(function(script, textStatus) {
				$.getScript("/js/libs/Detector.js").done(function(script, textStatus) {
					$.getScript("/js/libs/Tween.js").done(function(script, textStatus) {
						$.getScript("/js/libs/globe.js").done(function(script, textStatus) {
							var years = ['1990','1995','2000'];
							var container = document.getElementById(item_id);
							var globe = new DAT.Globe(container);
							console.log(globe);
							var i, tweens = [];

							var settime = function(globe, t) {
							return function() {
							  new TWEEN.Tween(globe).to({time: t/years.length},500).easing(TWEEN.Easing.Cubic.EaseOut).start();
							  var y = document.getElementById('year'+years[t]);
							  if (y.getAttribute('class') === 'year active') {
							    return;
							  }
							  var yy = document.getElementsByClassName('year');
							  for(i=0; i<yy.length; i++) {
							    yy[i].setAttribute('class','year');
							  }
							  y.setAttribute('class', 'year active');
							};
							};

							var xhr;
							TWEEN.start();


							xhr = new XMLHttpRequest();
							xhr.open('GET', '/fakedata/population909500.json', true);
							xhr.onreadystatechange = function(e) {
							if (xhr.readyState === 4) {
							  if (xhr.status === 200) {
							    var data = JSON.parse(xhr.responseText);
							    window.data = data;
							    for (i=0;i<data.length;i++) {
							      globe.addData(data[i][1], {format: 'magnitude', name: data[i][0], animated: true});
							    }
							    globe.createPoints();
							    settime(globe,0)();
							    globe.animate();
							  }
							}
							};
							xhr.send(null);
						});
					});
				});
			});
		});
	});
});