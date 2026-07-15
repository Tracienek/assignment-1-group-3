// Image Lightbox System Functions
function viewImage(imageSrc) {
  const portal = document.getElementById('lightboxPortal');
  const enlargedImage = document.getElementById('lightboxImage');
  if (portal && enlargedImage) {
    enlargedImage.src = imageSrc;
    portal.style.display = 'flex';
  }
}

function closeImage() {
  const portal = document.getElementById('lightboxPortal');
  if (portal) {
    portal.style.display = 'none';
  }
}

// Safely initialize external icon frameworks once the DOM loads
document.addEventListener('DOMContentLoaded', () => {
  if (typeof lucide !== 'undefined') {
    lucide.createIcons();
  }
});