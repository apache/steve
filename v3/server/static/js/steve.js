/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

/**
 * Common JavaScript utilities for the Apache STeVe voting system
 */

/**
 * Show a Bootstrap modal by ID
 * @param {string} modalId - The ID of the modal element
 * @returns {bootstrap.Modal} The modal instance
 */
function showModal(modalId) {
  const modal = new bootstrap.Modal(document.getElementById(modalId));
  modal.show();
  return modal;
}

/**
 * Validate that a required field has a value
 * @param {string} fieldId - The ID of the input field
 * @returns {boolean} True if valid, false otherwise
 */
function validateRequiredField(fieldId) {
  const field = document.getElementById(fieldId);
  const value = field.value.trim();
  
  if (!value) {
    field.classList.add('is-invalid');
    return false;
  }
  field.classList.remove('is-invalid');
  return true;
}

/**
 * Submit a form with loading state on the submit button
 * @param {string} formId - The ID of the form to submit
 * @param {string} buttonId - The ID of the button to show loading state
 * @param {string} loadingText - Text to display during loading (default: 'Submitting...')
 */
function submitFormWithLoading(formId, buttonId, loadingText = 'Submitting...') {
  const form = document.getElementById(formId);
  const button = document.getElementById(buttonId);
  
  // Store original button state
  const originalHTML = button.innerHTML;
  
  // Disable button and show loading state
  button.disabled = true;
  button.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>${loadingText}`;
  
  // Submit the form
  form.submit();
  
  // Note: Button will be reset when page reloads after submission
  // If submission fails and page doesn't reload, you may want to add error handling
}
