// Cuestionario reutilizable con corrección inmediata.
//
// Uso en una lección:
//   <div class="quiz" data-quiz>
//     <script type="application/json">
//       [{ "q": "Pregunta", "options": ["A", "B", "C", "D"], "answer": 2, "explain": "Por qué" }]
//     </script>
//   </div>
//   <script src="../assets/quiz.js"></script>
//
// Cada pregunta se responde una sola vez (sin pistas: el primer intento es el que cuenta para
// la recuperación activa). Al final se muestra la puntuación y se puede repetir.

(function () {
  function render(container) {
    const data = JSON.parse(container.querySelector('script[type="application/json"]').textContent)
    const list = document.createElement('div')
    container.appendChild(list)
    let answered = 0
    let correct = 0

    const score = document.createElement('p')
    score.className = 'quiz-score'
    score.hidden = true

    const retry = document.createElement('button')
    retry.className = 'quiz-retry'
    retry.textContent = 'Repetir el cuestionario'
    retry.hidden = true
    retry.addEventListener('click', () => {
      list.remove()
      score.remove()
      retry.remove()
      render(container)
    })

    data.forEach((item, index) => {
      const block = document.createElement('div')
      block.className = 'quiz-question'

      const question = document.createElement('p')
      question.className = 'q'
      question.textContent = `${index + 1}. ${item.q}`
      block.appendChild(question)

      const options = document.createElement('div')
      options.className = 'quiz-options'
      const feedback = document.createElement('p')
      feedback.className = 'quiz-feedback'
      feedback.hidden = true

      item.options.forEach((text, optionIndex) => {
        const button = document.createElement('button')
        button.type = 'button'
        button.textContent = text
        button.addEventListener('click', () => {
          const isRight = optionIndex === item.answer
          answered++
          if (isRight) correct++
          options.querySelectorAll('button').forEach((b, i) => {
            b.disabled = true
            if (i === item.answer) b.classList.add('correct')
          })
          if (!isRight) button.classList.add('wrong')
          feedback.hidden = false
          feedback.className = `quiz-feedback ${isRight ? 'ok' : 'bad'}`
          feedback.textContent = `${isRight ? '✔ Correcto.' : '✘ No.'} ${item.explain}`
          if (answered === data.length) {
            score.hidden = false
            score.textContent = `Resultado: ${correct} de ${data.length}. Anótalo en tu respuesta al profesor.`
            retry.hidden = false
          }
        })
        options.appendChild(button)
      })

      block.appendChild(options)
      block.appendChild(feedback)
      list.appendChild(block)
    })

    container.appendChild(score)
    container.appendChild(retry)
  }

  document.querySelectorAll('[data-quiz]').forEach(render)
})()
