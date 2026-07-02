const MAX_PHOTO_SIZE = 200 * 1024;

document.addEventListener("change", (event) => {
  if (event.target && event.target.id === "photo-input") {
    const file = event.target.files[0];
    if (file && file.size > MAX_PHOTO_SIZE) {
      alert("Размер фото не должен превышать 200 кБ.");
      event.target.value = "";
    }
  }
});
