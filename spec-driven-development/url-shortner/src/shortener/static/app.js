"use strict";

const COPIED_RESET_MS = 2000;

function fillTimeZoneFields() {
  const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  for (const input of document.querySelectorAll("input[name=time_zone]")) {
    input.value = timeZone;
  }
}

async function copyFromTarget(button) {
  const input = document.getElementById(button.dataset.copyTarget);
  const status = document.querySelector("[aria-live=polite]");
  try {
    await navigator.clipboard.writeText(input.value);
  } catch {
    input.focus();
    input.select();
    status.textContent = "Press Ctrl+C to copy";
    return;
  }
  button.textContent = "Copied";
  status.textContent = "Copied";
  setTimeout(() => {
    button.textContent = "Copy";
    status.textContent = "";
  }, COPIED_RESET_MS);
}

document.addEventListener("DOMContentLoaded", () => {
  fillTimeZoneFields();
  for (const button of document.querySelectorAll("[data-copy-target]")) {
    button.addEventListener("click", () => copyFromTarget(button));
  }
});
