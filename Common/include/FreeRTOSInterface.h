/**
  *****************************************************************************
  * @file    FreeRTOSInterface.h
  * @author  Izaak Niksan
  * @brief   Defines an abstract interface of FreeRTOS functions.
  *
  * @defgroup Header
  * @ingroup FreeRTOS_Interface
  * @{
  *****************************************************************************
  */




#ifndef FREERTOS_INTERFACE_H
#define FREERTOS_INTERFACE_H




/********************************* Includes **********************************/
#include <cstdint>

#include "SystemConf.h"
#include "cmsis_os.h"




/***************************** FreeRTOS_Interface ****************************/
namespace FreeRTOS_Interface {
// Classes and structs
// ----------------------------------------------------------------------------
class FreeRTOSInterface {
public:
    virtual ~FreeRTOSInterface() {}

    virtual BaseType_t OS_xTaskNotifyWait(
        uint32_t ulBitsToClearOnEntry,
        uint32_t ulBitsToClearOnExit,
        uint32_t *pulNotificationValue,
        TickType_t xTicksToWait
    ) const = 0;

    virtual BaseType_t OS_xQueueReceive(
        QueueHandle_t xQueue,
        void *pvBuffer,
        TickType_t xTicksToWait
    ) const = 0;

    virtual BaseType_t OS_xQueueSend(
        QueueHandle_t xQueue,
        const void * pvItemToQueue,
        TickType_t xTicksToWait
    ) const = 0;

    virtual BaseType_t OS_xSemaphoreTake(
        SemaphoreHandle_t xSemaphore,
        TickType_t xBlockTime
    ) const = 0;

    virtual BaseType_t OS_xSemaphoreGive(
        SemaphoreHandle_t xSemaphore
    ) const = 0;

    virtual void OS_vTaskDelayUntil(
        TickType_t * const pxPreviousWakeTime,
        const TickType_t xTimeIncrement
    ) const = 0;

    virtual osStatus OS_osDelay (
        uint32_t millisec
    ) const = 0;
};

} // end namespace FreeRTOS_Interface

/**
 * @}
 */
/* end - Header */

#endif /* FREERTOS_INTERFACE_H */
