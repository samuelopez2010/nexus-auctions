
document.addEventListener('DOMContentLoaded', function () {
    function updateTimers() {
        const timers = document.querySelectorAll('.auction-timer');
        timers.forEach(timer => {
            const endTimeStr = timer.getAttribute('data-end-time');
            if (!endTimeStr) return;

            const endTime = new Date(endTimeStr).getTime();
            const now = new Date().getTime();
            const distance = endTime - now;

            if (distance < 0) {
                timer.innerHTML = "Ended";
                timer.classList.add('text-danger');
                // Optional: reload page if it just ended?
                return;
            }

            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);

            let display = "";
            if (days > 0) display += days + "d ";
            if (hours > 0 || days > 0) display += hours + "h ";
            display += minutes + "m " + seconds + "s";

            timer.innerHTML = display;
        });
    }

    setInterval(updateTimers, 1000);
    updateTimers(); // Initial call
});
