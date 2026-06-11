// Tab switching logic cho smart_eda_report.html
// Member C có thể mở rộng thêm animation, keyboard navigation, etc.

function showTab(id) {
  document.querySelectorAll('.tab-content').forEach(function(el) {
    el.style.display = 'none';
  });
  document.querySelectorAll('.tab').forEach(function(el) {
    el.classList.remove('active');
  });
  document.getElementById('tab-' + id).style.display = 'block';
  event.target.classList.add('active');
}
